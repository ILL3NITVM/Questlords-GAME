"""Scan and fingerprint a directory of existing Octavia photographs.

Produces one record per image with everything later stages need:
identity hash, perceptual hash, dimensions, aspect bucket, exposure stats
and quality flags.

Nothing here modifies or moves the source files. The dataset is read-only;
curation decisions are recorded as metadata and only materialised at export.
"""
from __future__ import annotations

import hashlib
import pathlib
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from PIL import Image, ImageStat

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

# SDXL-style training buckets (w, h). A source image is assigned to the
# bucket with the closest aspect ratio; wildly off-ratio images get flagged
# because bucket cropping will eat the subject.
ASPECT_BUCKETS = [
    (1024, 1024), (896, 1152), (832, 1216), (768, 1344), (640, 1536),
    (1152, 896), (1216, 832), (1344, 768), (1536, 640),
]


@dataclass
class ImageRecord:
    path: str
    filename: str
    bytes: int
    sha256: str
    dhash: str
    width: int
    height: int
    aspect: float
    mode: str
    bucket: str
    bucket_aspect_error: float
    mean_luma: float
    rms_contrast: float
    saturation: float
    flags: List[str] = field(default_factory=list)
    caption: Optional[str] = None
    cluster: Optional[int] = None
    selected: bool = True
    reject_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def dhash(img: Image.Image, size: int = 8) -> str:
    """64-bit difference hash. Robust to rescaling and mild recompression,
    which is exactly what near-duplicate detection needs."""
    small = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    pixels = list(small.tobytes())  # row-major L bytes; avoids deprecated getdata()
    bits = 0
    n = 0
    for row in range(size):
        base = row * (size + 1)
        for col in range(size):
            bits = (bits << 1) | (1 if pixels[base + col] > pixels[base + col + 1] else 0)
            n += 1
    return f"{bits:0{n // 4}x}"


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def _bucket_for(width: int, height: int) -> tuple[str, float]:
    aspect = width / height if height else 0.0
    best, best_err = ASPECT_BUCKETS[0], float("inf")
    for bw, bh in ASPECT_BUCKETS:
        err = abs((bw / bh) - aspect)
        if err < best_err:
            best, best_err = (bw, bh), err
    return f"{best[0]}x{best[1]}", round(best_err, 4)


def iter_images(root: pathlib.Path) -> Iterator[pathlib.Path]:
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMAGE_EXT:
            yield p


def inspect(path: pathlib.Path, cfg: Dict[str, Any]) -> ImageRecord:
    data = path.read_bytes()
    with Image.open(path) as im:
        im.load()
        width, height = im.size
        mode = im.mode
        rgb = im.convert("RGB")
        ph = dhash(rgb)
        stat = ImageStat.Stat(rgb.convert("L"))
        mean_luma = round(stat.mean[0], 2)
        rms_contrast = round(stat.stddev[0], 2)
        hsv_stat = ImageStat.Stat(rgb.convert("HSV"))
        saturation = round(hsv_stat.mean[1], 2)

    bucket, bucket_err = _bucket_for(width, height)
    rec = ImageRecord(
        path=str(path), filename=path.name, bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(), dhash=ph,
        width=width, height=height, aspect=round(width / height, 4) if height else 0.0,
        mode=mode, bucket=bucket, bucket_aspect_error=bucket_err,
        mean_luma=mean_luma, rms_contrast=rms_contrast, saturation=saturation,
    )

    q = cfg.get("quality", {})
    min_side = int(q.get("min_side", 768))
    if min(width, height) < min_side:
        rec.flags.append(f"low_resolution({min(width, height)}px < {min_side})")
    if bucket_err > float(q.get("max_aspect_error", 0.25)):
        rec.flags.append(f"extreme_aspect({rec.aspect})")
    if mean_luma < float(q.get("min_luma", 28)):
        rec.flags.append(f"underexposed(luma {mean_luma})")
    if mean_luma > float(q.get("max_luma", 232)):
        rec.flags.append(f"overexposed(luma {mean_luma})")
    if rms_contrast < float(q.get("min_contrast", 18)):
        rec.flags.append(f"flat_contrast(rms {rms_contrast})")
    if mode not in ("RGB", "L") and "A" in mode:
        rec.flags.append("has_alpha_channel")
    return rec


def scan(root: pathlib.Path, cfg: Dict[str, Any]) -> List[ImageRecord]:
    records: List[ImageRecord] = []
    errors: List[Dict[str, str]] = []
    for p in iter_images(root):
        try:
            records.append(inspect(p, cfg))
        except Exception as exc:
            errors.append({"path": str(p), "error": f"{type(exc).__name__}: {exc}"})
    if errors:
        for e in errors:
            rec = ImageRecord(path=e["path"], filename=pathlib.Path(e["path"]).name,
                              bytes=0, sha256="", dhash="0" * 16, width=0, height=0,
                              aspect=0.0, mode="?", bucket="?", bucket_aspect_error=0.0,
                              mean_luma=0.0, rms_contrast=0.0, saturation=0.0,
                              flags=["unreadable"], selected=False,
                              reject_reason=e["error"])
            records.append(rec)
    return records
