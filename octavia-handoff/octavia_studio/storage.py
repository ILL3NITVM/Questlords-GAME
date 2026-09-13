"""SQLite catalog and verified, write-once content storage."""
from __future__ import annotations

import hashlib
import fcntl
import json
import os
import re
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY, applied TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS shoots(shoot_id TEXT PRIMARY KEY, name TEXT NOT NULL,
 created TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', allowed_repetition TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS wardrobe(wardrobe_item_id TEXT PRIMARY KEY, name TEXT NOT NULL,
 category TEXT NOT NULL, material TEXT, primary_color TEXT, secondary_color TEXT, fit TEXT,
 source_reference TEXT, first_seen TEXT NOT NULL, canon_status TEXT NOT NULL DEFAULT 'candidate',
 ownership TEXT NOT NULL DEFAULT 'inspiration' CHECK(ownership IN ('established','inspiration','candidate')),
 notes TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS outfits(outfit_id TEXT PRIMARY KEY, name TEXT NOT NULL, notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS outfit_items(outfit_id TEXT REFERENCES outfits, wardrobe_item_id TEXT REFERENCES wardrobe,
 PRIMARY KEY(outfit_id,wardrobe_item_id));
CREATE TABLE IF NOT EXISTS wardrobe_evidence(evidence_id TEXT PRIMARY KEY,
 wardrobe_item_id TEXT NOT NULL REFERENCES wardrobe, asset_id TEXT NOT NULL REFERENCES assets,
 region TEXT NOT NULL, confidence TEXT NOT NULL, reviewer TEXT NOT NULL, notes TEXT NOT NULL,
 created TEXT NOT NULL, UNIQUE(wardrobe_item_id,asset_id,region));
CREATE TABLE IF NOT EXISTS wardrobe_reviews(asset_id TEXT PRIMARY KEY REFERENCES assets,
 status TEXT NOT NULL, reviewer TEXT NOT NULL, notes TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rooms(room_id TEXT PRIMARY KEY, name TEXT NOT NULL, architecture TEXT NOT NULL,
 furniture TEXT DEFAULT '', notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS texture_packs(texture_pack_id TEXT PRIMARY KEY, room_id TEXT NOT NULL REFERENCES rooms,
 name TEXT NOT NULL, treatment TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS blobs(sha256 TEXT PRIMARY KEY, path TEXT NOT NULL UNIQUE, bytes INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS assets(asset_id TEXT PRIMARY KEY, original_filename TEXT NOT NULL,
 source TEXT NOT NULL, created_at TEXT, imported_at TEXT NOT NULL, width INTEGER NOT NULL,
 height INTEGER NOT NULL, aspect_ratio REAL NOT NULL, sha256 TEXT NOT NULL REFERENCES blobs,
 perceptual_hash TEXT NOT NULL, shoot_id TEXT REFERENCES shoots, outfit_id TEXT REFERENCES outfits,
 room_id TEXT REFERENCES rooms, texture_pack_id TEXT REFERENCES texture_packs,
 pose TEXT NOT NULL DEFAULT '[]', framing TEXT, expression TEXT, hair_state TEXT,
 pendant_present INTEGER CHECK(pendant_present IN (0,1) OR pendant_present IS NULL),
 canon_status TEXT NOT NULL DEFAULT 'unreviewed' CHECK(canon_status IN ('unreviewed','reference','approved','rejected','derivative')),
 quality_status TEXT NOT NULL DEFAULT 'unreviewed', continuity_status TEXT,
 notes TEXT NOT NULL DEFAULT '', parent_asset_id TEXT REFERENCES assets,
 kind TEXT NOT NULL DEFAULT 'portrait', state TEXT NOT NULL DEFAULT '{}',
 metrics TEXT NOT NULL, recipe_key TEXT UNIQUE);
CREATE INDEX IF NOT EXISTS assets_hash ON assets(sha256);
CREATE TABLE IF NOT EXISTS origins(path TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets,
 source TEXT NOT NULL, seen TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS shoot_assets(shoot_id TEXT REFERENCES shoots, asset_id TEXT REFERENCES assets,
 PRIMARY KEY(shoot_id, asset_id));
CREATE TABLE IF NOT EXISTS asset_links(child TEXT REFERENCES assets, parent TEXT REFERENCES assets,
 relation TEXT NOT NULL, PRIMARY KEY(child,parent,relation));
CREATE TABLE IF NOT EXISTS documents(document_id TEXT PRIMARY KEY, original_path TEXT NOT NULL,
 sha256 TEXT NOT NULL, archive_path TEXT NOT NULL, kind TEXT, status TEXT, imported_at TEXT NOT NULL,
 UNIQUE(original_path,sha256));
CREATE TABLE IF NOT EXISTS canon_revisions(revision_id INTEGER PRIMARY KEY, created TEXT NOT NULL,
 reason TEXT NOT NULL, identity TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(event_id INTEGER PRIMARY KEY, created TEXT NOT NULL,
 action TEXT NOT NULL, subject TEXT NOT NULL, details TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reports(report_id TEXT PRIMARY KEY, shoot_id TEXT, kind TEXT NOT NULL,
 created TEXT NOT NULL, json_path TEXT NOT NULL, summary_path TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY, kind TEXT NOT NULL, target TEXT NOT NULL,
 request TEXT NOT NULL, status TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL,
 pid INTEGER, error TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS job_items(job_id TEXT REFERENCES jobs, asset_id TEXT REFERENCES assets,
 status TEXT NOT NULL DEFAULT 'pending', result TEXT, error TEXT, PRIMARY KEY(job_id,asset_id));
CREATE TABLE IF NOT EXISTS sheet_members(sheet_id TEXT REFERENCES assets, source_asset_id TEXT REFERENCES assets,
 position INTEGER NOT NULL, bounds TEXT NOT NULL, PRIMARY KEY(sheet_id,position));
CREATE TABLE IF NOT EXISTS review_decisions(asset_id TEXT REFERENCES assets, shoot_id TEXT NOT NULL,
 issue_key TEXT NOT NULL, reason TEXT NOT NULL, created TEXT NOT NULL,
 PRIMARY KEY(asset_id,shoot_id,issue_key));
CREATE TRIGGER IF NOT EXISTS immutable_asset_content BEFORE UPDATE OF
 sha256,width,height,aspect_ratio,parent_asset_id,recipe_key,source ON assets
 BEGIN SELECT RAISE(ABORT,'Asset content and lineage are immutable; create a derivative'); END;
CREATE TRIGGER IF NOT EXISTS immutable_blobs BEFORE UPDATE ON blobs
 BEGIN SELECT RAISE(ABORT,'Blobs are immutable'); END;
CREATE TRIGGER IF NOT EXISTS no_asset_delete BEFORE DELETE ON assets
 BEGIN SELECT RAISE(ABORT,'Automatic deletion is not supported'); END;
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def packed(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def identifier(value):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}', value):
        raise ValueError('IDs must use letters, numbers, dots, underscores or hyphens')
    return value


def write_once(path, data):
    """Publish a fully fsynced file without replacing anything, even on a race."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o444)
        try:
            os.link(temporary, str(path))
        except FileExistsError:
            if file_hash(path) != digest(data):
                raise ValueError('Refusing to replace different content: {}'.format(path))
        directory = os.open(str(path.parent), os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)
    return path


class Studio:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.root / 'studio.sqlite3'), timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version > 1:
            raise ValueError('Database is newer than this application')
        self.db.executescript(SCHEMA)
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO schema_versions VALUES(1,?)', (now(),))
            self.db.execute('PRAGMA user_version=1')

    def close(self):
        self.db.close()

    def rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args)]

    def log(self, action, subject, details):
        self.db.execute('INSERT INTO audit(created,action,subject,details) VALUES(?,?,?,?)',
                        (now(), action, subject, packed(details)))

    def shoot(self, shoot_id, name=None, allowed=None):
        identifier(shoot_id)
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO shoots VALUES(?,?,?,?,?)',
                            (shoot_id, name or shoot_id, now(), '', packed(allowed or [])))

    def get(self, value):
        rows = self.rows('SELECT * FROM assets WHERE asset_id=?', (value,))
        if not rows:
            rows = self.rows('SELECT * FROM assets WHERE original_filename=?', (Path(value).name,))
        if not rows:
            rows = self.rows('SELECT * FROM assets WHERE asset_id LIKE ?', (value + '%',))
        if len(rows) != 1:
            raise ValueError('Asset not found or ambiguous: {}'.format(value))
        return rows[0]

    def resolve_target(self, target):
        if target == 'latest':
            row = self.db.execute('SELECT shoot_id FROM shoots WHERE shoot_id NOT IN '
                                  "('inbox','legacy-references','legacy-sheets','legacy-archive') "
                                  'ORDER BY created DESC,rowid DESC LIMIT 1').fetchone()
            if not row:
                raise ValueError('No shoots yet')
            target = row[0]
        return target

    def target_shoot(self, target):
        target = self.resolve_target(target)
        if self.db.execute('SELECT 1 FROM shoots WHERE shoot_id=?', (target,)).fetchone():
            return target
        return self.get(target)['shoot_id']

    def select(self, target, derivatives=False):
        target = self.resolve_target(target)
        if self.db.execute('SELECT 1 FROM shoots WHERE shoot_id=?', (target,)).fetchone():
            sql = 'SELECT a.* FROM assets a JOIN shoot_assets s USING(asset_id) WHERE s.shoot_id=?'
            if not derivatives:
                sql += " AND a.kind NOT IN ('polished','export','sheet','before_after','wardrobe-detail')"
            return self.rows(sql + ' ORDER BY a.imported_at,a.asset_id', (target,))
        return [self.get(target)]

    def path(self, asset):
        row = self.db.execute('SELECT path FROM blobs WHERE sha256=?', (asset['sha256'],)).fetchone()
        path = self.root / row[0]
        if file_hash(path) != asset['sha256']:
            raise ValueError('Integrity mismatch: {}'.format(asset['asset_id']))
        return path

    def _blob(self, data, suffix):
        sha = digest(data)
        old = self.db.execute('SELECT path FROM blobs WHERE sha256=?', (sha,)).fetchone()
        path = self.root / (old[0] if old else 'originals/{}/{}{}'.format(sha[:2], sha, suffix.lower()))
        write_once(path, data)
        self.db.execute('INSERT OR IGNORE INTO blobs VALUES(?,?,?)',
                        (sha, str(path.relative_to(self.root)), len(data)))
        return sha

    def import_image(self, path, shoot_id='inbox', source='import', kind='portrait'):
        from .imaging import inspect_bytes
        path = Path(path).expanduser().resolve()
        data = path.read_bytes()
        sha = digest(data)
        self.shoot(shoot_id)
        existing = self.rows('SELECT * FROM assets WHERE sha256=? AND parent_asset_id IS NULL '
                             'AND recipe_key IS NULL LIMIT 1', (sha,))
        if existing:
            asset_id = existing[0]['asset_id']
            self.path(existing[0])
        else:
            info = inspect_bytes(data)
            asset_id = 'a-' + sha[:16]
            created = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
            with self.db:
                self._blob(data, path.suffix)
                self.db.execute('''INSERT INTO assets(asset_id,original_filename,source,created_at,
                    imported_at,width,height,aspect_ratio,sha256,perceptual_hash,shoot_id,kind,metrics)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (asset_id, path.name, source, created, now(), info['width'], info['height'],
                     info['width']/info['height'], sha, info['phash'], shoot_id, kind, packed(info)))
                self.log('import', asset_id, {'origin': str(path), 'created_at_basis': 'filesystem mtime, not generation time'})
        with self.db:
            old = self.db.execute('SELECT asset_id FROM origins WHERE path=?', (str(path),)).fetchone()
            if old and old[0] != asset_id:
                self.log('origin_changed', asset_id, {'path': str(path), 'previous_asset': old[0]})
            self.db.execute('INSERT OR REPLACE INTO origins VALUES(?,?,?,?)', (str(path), asset_id, source, now()))
            self.db.execute('INSERT OR IGNORE INTO shoot_assets VALUES(?,?)', (shoot_id, asset_id))
        return asset_id

    def derivative(self, image, parents, kind, recipe, metadata=None, suffix='.png'):
        key = digest(packed({'version': 1, 'kind': kind, 'parents': parents, 'recipe': recipe}).encode())
        directory = self.root / 'locks'
        directory.mkdir(exist_ok=True)
        with open(directory / ('recipe-' + key + '.lock'), 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return self._derivative(image, parents, kind, recipe, metadata, suffix)

    def _derivative(self, image, parents, kind, recipe, metadata=None, suffix='.png'):
        from .imaging import encode, inspect_bytes
        key = digest(packed({'version': 1, 'kind': kind, 'parents': parents, 'recipe': recipe}).encode())
        old = self.rows('SELECT * FROM assets WHERE recipe_key=?', (key,))
        if old:
            self.path(old[0])
            return old[0]['asset_id']
        parent = self.get(parents[0])
        for source in parents:
            self.path(self.get(source))
        data = encode(image, suffix, metadata or {})
        dest = self.root / 'derivatives' / kind / (key + suffix)
        if dest.exists():
            # Recover a verified publication after a crash before the database commit.
            # ICC creation timestamps can differ even for identical rendered pixels.
            from .imaging import decode
            published = dest.read_bytes()
            expected, actual = decode(data), decode(published)
            if expected.size != actual.size or expected.mode != actual.mode or expected.tobytes() != actual.tobytes():
                raise ValueError('Unregistered output differs from expected recipe: ' + str(dest))
            data = published
        info = inspect_bytes(data)
        write_once(dest, data)
        asset_id = 'd-' + key[:16]
        sha = digest(data)
        state = json.loads(parent['state']) if kind == 'polished' else {}
        state['transform'] = recipe
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO blobs VALUES(?,?,?)',
                            (sha, str(dest.relative_to(self.root)), len(data)))
            self.db.execute('''INSERT INTO assets(asset_id,original_filename,source,created_at,imported_at,
                width,height,aspect_ratio,sha256,perceptual_hash,shoot_id,parent_asset_id,kind,
                canon_status,metrics,recipe_key,state) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (asset_id,dest.name,'studio-derivative',now(),now(),info['width'],info['height'],
                 info['width']/info['height'],sha,info['phash'],parent['shoot_id'],parent['asset_id'],
                 kind,'derivative',packed(info),key,packed(state)))
            for source in parents:
                self.db.execute('INSERT OR IGNORE INTO asset_links VALUES(?,?,?)', (asset_id,source,kind))
            if parent['shoot_id']:
                self.db.execute('INSERT OR IGNORE INTO shoot_assets VALUES(?,?)', (parent['shoot_id'],asset_id))
            if kind == 'polished':
                fields = ['pose','framing','expression','hair_state','pendant_present','outfit_id','room_id','texture_pack_id']
                self.db.execute('UPDATE assets SET ' + ','.join(f+'=?' for f in fields) + ' WHERE asset_id=?',
                                [parent[f] for f in fields] + [asset_id])
            self.log(kind, asset_id, {'parents':parents,'recipe':recipe,'sha256':sha,'output':str(dest)})
        return asset_id

    def annotate(self, asset_id, values, evidence='human observation'):
        from .imaging import valid_box
        allowed = {'pose','framing','expression','hair_state','pendant_present','outfit_id','room_id',
                   'texture_pack_id','notes','state','kind'}
        if set(values) - allowed:
            raise ValueError('Unsupported metadata field; canon changes require canon approve')
        row = self.get(asset_id)
        values = dict(values)
        if 'pose' in values:
            if not isinstance(values['pose'], list) or not all(isinstance(x,str) for x in values['pose']):
                raise ValueError('pose must be a list of tags')
            values['pose'] = packed(values['pose'])
        if 'state' in values:
            state = json.loads(row['state'])
            if not isinstance(values['state'], dict):
                raise ValueError('state must be an object')
            for key, value in values['state'].items():
                if key.endswith('_roi'):
                    valid_box(value)
            state.update(values['state'])
            state['annotation_evidence'] = evidence
            values['state'] = packed(state)
        if values.get('pendant_present') not in (None, True, False, 0, 1):
            raise ValueError('pendant_present must be true, false or null')
        room = values.get('room_id', row['room_id'])
        pack = values.get('texture_pack_id', row['texture_pack_id'])
        if pack:
            p = self.db.execute('SELECT room_id FROM texture_packs WHERE texture_pack_id=?', (pack,)).fetchone()
            if not p or p[0] != room:
                raise ValueError('Texture pack must belong to the annotated room')
        if not values:
            return
        with self.db:
            self.db.execute('UPDATE assets SET ' + ','.join(k+'=?' for k in values) + ' WHERE asset_id=?',
                            list(values.values())+[row['asset_id']])
            self.log('annotate', row['asset_id'], {'before': {k:row[k] for k in values},'after':values,'evidence':evidence})

    def approve(self, asset_id, reason, allow_derivative=False, status='approved'):
        if not reason.strip():
            raise ValueError('A reason is required for canon changes')
        row = self.get(asset_id)
        if (row['parent_asset_id'] or row['canon_status']=='derivative') and not allow_derivative:
            raise ValueError('Derivative canon promotion requires --allow-derivative and a reason')
        self.path(row)
        backup = self.backup()
        with self.db:
            self.db.execute('UPDATE assets SET canon_status=? WHERE asset_id=?', (status,row['asset_id']))
            self.log('canon_approval',row['asset_id'],{'old':row['canon_status'],'new':status,'reason':reason,'backup':str(backup)})

    def backup(self):
        path = self.root / 'backups' / ('studio-' + uuid.uuid4().hex + '.sqlite3')
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.pending')
        with sqlite3.connect(str(temporary)) as dest:
            self.db.backup(dest)
            if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Backup verification failed')
        write_once(path, temporary.read_bytes())
        temporary.unlink()
        return path

    def report(self, kind, shoot_id, content, summary):
        report_id = 'r-' + uuid.uuid4().hex[:16]
        directory = self.root / 'reports' / identifier(shoot_id or 'assets')
        json_path = directory / (report_id + '.json')
        md_path = directory / (report_id + '.md')
        content = dict(content, report_id=report_id, created=now(), kind=kind, shoot_id=shoot_id)
        write_once(json_path, (json.dumps(content, indent=2, sort_keys=True, allow_nan=False)+'\n').encode())
        write_once(md_path, ('# Octavia Studio: '+kind+'\n\n'+summary+'\n').encode())
        with self.db:
            self.db.execute('INSERT INTO reports VALUES(?,?,?,?,?,?)',
                            (report_id,shoot_id,kind,now(),str(json_path),str(md_path)))
        return {'report_id':report_id,'json':str(json_path),'summary':str(md_path)}
