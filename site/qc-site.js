(()=>{'use strict';
const icon=n=>`<svg class="qc-ic" aria-hidden="true" focusable="false"><use href="/assets/icons.svg#i-${n}"/></svg>`;

/* ── Toasts: one polite live region; newest replaces oldest beyond three. ── */
const toastRoot=document.querySelector('.qc-toasts');
function toast(msg,{icon:ic='check',action=null,timeout=3200}={}){
  if(!toastRoot)return;
  // Flapping events (network, repeated taps) must not stack identical messages.
  for(const old of toastRoot.children)if(old.querySelector('span')?.textContent===msg&&!old.classList.contains('out'))return;
  const t=document.createElement('div');t.className='qc-toast';t.innerHTML=icon(ic)+'<span></span>';t.querySelector('span').textContent=msg;
  if(action){const b=document.createElement('button');b.type='button';b.textContent=action.label;b.addEventListener('click',()=>{action.run();t.remove()});t.appendChild(b)}
  if(action)t.dataset.keep='1';toastRoot.appendChild(t);
  const plain=()=>[...toastRoot.children].filter(x=>!x.dataset.keep);while(toastRoot.children.length>3&&plain().length)plain()[0].remove();
  if(timeout)setTimeout(()=>{t.classList.add('out');setTimeout(()=>t.remove(),220)},timeout);
}
window.qcToast=toast;

/* ── Glossary: filter with a live count and highlighted matches, "/" to focus, Esc to clear, ?q= kept in the URL. ── */
const s=document.getElementById('glossarySearch'),list=document.getElementById('glossaryList'),status=document.getElementById('glossaryStatus');
if(s&&list){
  const terms=[...list.querySelectorAll('.qc-term')],total=terms.length;
  // Highlighting splits text nodes; the query is never parsed as HTML.
  const unmark=el=>{for(const m of [...el.querySelectorAll('mark')])m.replaceWith(document.createTextNode(m.textContent));el.normalize()};
  const mark=(el,q)=>{const walk=document.createTreeWalker(el,NodeFilter.SHOW_TEXT,{acceptNode:n=>n.parentElement.closest('.qc-anchor')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT});
    const nodes=[];while(walk.nextNode())nodes.push(walk.currentNode);
    for(const n of nodes){const t=n.nodeValue,lo=t.toLowerCase();let i=lo.indexOf(q);if(i<0)continue;const f=document.createDocumentFragment();let from=0;
      while(i>=0){f.append(t.slice(from,i));const m=document.createElement('mark');m.textContent=t.slice(i,i+q.length);f.append(m);from=i+q.length;i=lo.indexOf(q,from)}
      f.append(t.slice(from));n.replaceWith(f)}};
  const apply=(push)=>{
    const q=s.value.trim().toLowerCase();let shown=0;
    for(const x of terms){unmark(x);const hit=!q||((x.dataset.term||'')+' '+x.textContent.toLowerCase()).includes(q);x.hidden=!hit;if(hit){shown++;if(q)mark(x,q)}}
    if(status)status.textContent=q?(shown?`${shown} of ${total} terms match "${s.value.trim()}"`:`No term matches "${s.value.trim()}". Try a shorter word.`):`${total} terms`;
    if(push){try{const u=new URL(location.href);q?u.searchParams.set('q',s.value.trim()):u.searchParams.delete('q');history.replaceState(null,'',u)}catch(_){}}
  };
  try{const q=new URL(location.href).searchParams.get('q');if(q)s.value=q}catch(_){}
  s.addEventListener('input',()=>apply(true));
  s.addEventListener('keydown',e=>{if(e.key==='Escape'&&s.value){s.value='';apply(true)}});
  addEventListener('keydown',e=>{if(e.key==='/'&&document.activeElement!==s&&!e.metaKey&&!e.ctrlKey&&!e.altKey&&!/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName||'')){e.preventDefault();s.focus()}});
  // Following an A–Z or deep link while a filter hides the target clears the filter first.
  const reveal=id=>{const t=document.getElementById(id);if(t&&t.hidden){s.value='';apply(true);t.scrollIntoView()}};
  addEventListener('hashchange',()=>reveal(location.hash.slice(1)));
  for(const a of document.querySelectorAll('.qc-az a,.qc-term .qc-anchor'))a.addEventListener('click',()=>reveal(a.getAttribute('href').slice(1)));
  apply(false);
  if(location.hash)reveal(location.hash.slice(1));
}

/* Anchor links copy their URL when the clipboard is available; they still navigate otherwise. */
for(const a of document.querySelectorAll('.qc-anchor')){
  a.addEventListener('click',()=>{try{navigator.clipboard?.writeText(new URL(a.getAttribute('href'),location.href).href).then(()=>toast('Link copied',{icon:'link'}),()=>{})}catch(_){}});
}
/* Network state, reported only when it changes. */
addEventListener('offline',()=>toast('Offline · saved pages still open; nothing shown is live',{icon:'offline',timeout:6000}));
addEventListener('online',()=>toast('Back online',{icon:'check'}));

/* ── Bottom sheet: modal dialog with focus trap, Esc, backdrop, drag-to-dismiss, scroll lock and focus restore. ── */
function bottomSheet(sheet,{trigger=null,firstFocus=()=>null}={}){
  const panel=sheet.querySelector('.qc-sheet-panel');let lastFocus=null,hideTimer=0;
  const focusables=()=>[...panel.querySelectorAll('a[href],button:not([disabled])')].filter(el=>el.tabIndex!==-1);
  const open=()=>{clearTimeout(hideTimer);lastFocus=document.activeElement;sheet.hidden=false;document.documentElement.classList.add('qc-sheet-open');trigger?.setAttribute('aria-expanded','true');
    requestAnimationFrame(()=>{sheet.classList.add('open');(firstFocus()||panel).focus()})};
  const close=()=>{clearTimeout(hideTimer);sheet.classList.remove('open');trigger?.setAttribute('aria-expanded','false');document.documentElement.classList.remove('qc-sheet-open');panel.style.transform='';
    const done=()=>{sheet.hidden=true;lastFocus?.focus?.()};matchMedia('(prefers-reduced-motion: reduce)').matches?done():(hideTimer=setTimeout(done,200))};
  sheet.addEventListener('click',e=>{if(e.target.closest('[data-close]'))close()});
  sheet.addEventListener('keydown',e=>{
    if(e.key==='Escape'){e.preventDefault();close();return}
    if(e.key!=='Tab')return;const f=focusables();if(!f.length)return;const i=f.indexOf(document.activeElement);
    if(e.shiftKey&&i<=0){e.preventDefault();f[f.length-1].focus()}else if(!e.shiftKey&&i===f.length-1){e.preventDefault();f[0].focus()}
  });
  let y0=null;
  for(const el of [panel.querySelector('.qc-sheet-handle'),panel.querySelector('.qc-sheet-head')])el?.addEventListener('pointerdown',e=>{if(e.target.closest('button'))return;y0=e.clientY;panel.setPointerCapture?.(e.pointerId);panel.classList.add('dragging')});
  panel.addEventListener('pointermove',e=>{if(y0===null)return;panel.style.transform=`translateY(${Math.max(0,e.clientY-y0)}px)`});
  const end=e=>{if(y0===null)return;const d=e.clientY-y0;y0=null;panel.classList.remove('dragging');if(d>80)close();else panel.style.transform=''};
  panel.addEventListener('pointerup',end);panel.addEventListener('pointercancel',end);
  return {open,close,get isOpen(){return !sheet.hidden}};
}

/* MORE sheet */
const more=document.getElementById('qc-more'),moreBtn=document.querySelector('.qc-tab-more');
if(more&&moreBtn){
  const panel=more.querySelector('.qc-sheet-panel');
  const ctl=bottomSheet(more,{trigger:moreBtn,firstFocus:()=>panel.querySelector('a.qc-row[aria-current="page"]')||panel.querySelector('a.qc-row')});
  moreBtn.setAttribute('href','#qc-more');moreBtn.setAttribute('aria-expanded','false');
  moreBtn.addEventListener('click',e=>{e.preventDefault();ctl.isOpen?ctl.close():ctl.open()});
  /* Skin segmented control: shares the desk's preference key. GENESIS is the master skin; the desk's
     AURUM has no site counterpart and shows as REGALIA here, without being overwritten. */
  const KEY='quadcom-v57-skin',seg=[...panel.querySelectorAll('[data-skin]')],NAMES={genesis:'GENESIS skin on',regalia:'REGALIA skin on',off:'Skin off'};
  const cur=()=>{try{const k=localStorage.getItem(KEY);return k==='off'?'off':k==='regalia'||k==='aurum'?'regalia':'genesis'}catch(_){return 'genesis'}};
  const paint=()=>{const c=cur();for(const b of seg){const on=b.dataset.skin===c;b.setAttribute('aria-checked',String(on));b.tabIndex=on?0:-1}};
  for(const b of seg)b.addEventListener('click',()=>{const v=b.dataset.skin;try{const prev=localStorage.getItem(KEY);localStorage.setItem(KEY,v==='regalia'&&prev==='aurum'?'aurum':v)}catch(_){}
    document.documentElement.dataset.qcTexture=v;paint();toast(NAMES[v],{icon:'skin'})});
  panel.querySelector('.qc-seg')?.addEventListener('keydown',e=>{if(!/Arrow(Left|Right)/.test(e.key))return;e.preventDefault();const i=seg.findIndex(b=>b.getAttribute('aria-checked')==='true');const n=seg[(i+(e.key==='ArrowRight'?1:seg.length-1))%seg.length];n.click();n.focus()});
  paint();
}

/* ── Term previews: glossary terms in page copy open their definition in a sheet.
   Only the first mention per section is linked, headings and links are skipped, and
   without JavaScript the copy stays plain text. The glossary page is the single source. ── */
let glossDict=null;
const glossary=()=>glossDict||(glossDict=fetch('/glossary/').then(r=>r.ok?r.text():Promise.reject()).then(t=>{
    const doc=new DOMParser().parseFromString(t,'text/html'),out=[];
    for(const a of doc.querySelectorAll('#glossaryList .qc-term')){const h=a.querySelector('h3');const name=[...h.childNodes].filter(n=>n.nodeType===3).map(n=>n.nodeValue).join('').trim();
      const key=name.replace(/\s*\(.*\)$/,'');if(key.length<3||/^P0/.test(key))continue;out.push({id:a.id,name,key,def:a.querySelector('p').textContent})}
    return out.sort((x,y)=>y.key.length-x.key.length)}));
const copyRoot=document.querySelector('[data-glossary-links] .qc-grid');
if(copyRoot){
  const load=glossary;
  const esc=t=>t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const link=entries=>{
    for(const sec of copyRoot.querySelectorAll('.qc-panel')){
      const used=new Set();
      const walk=document.createTreeWalker(sec,NodeFilter.SHOW_TEXT,{acceptNode:n=>n.parentElement.closest('h1,h2,h3,a,button,.qc-tag,mark')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT});
      const nodes=[];while(walk.nextNode())nodes.push(walk.currentNode);
      for(const n of nodes){
        for(const e of entries){if(used.has(e.id))continue;const m=new RegExp(`\\b${esc(e.key)}\\b`,'i').exec(n.nodeValue);if(!m)continue;
          const b=document.createElement('button');b.type='button';b.className='qc-gterm';b.dataset.term=e.id;b.textContent=m[0];b.setAttribute('aria-haspopup','dialog');
          const after=n.splitText(m.index);after.nodeValue=after.nodeValue.slice(m[0].length);n.after(b);used.add(e.id);break}
      }
    }
  };
  let sheetCtl=null;const sheetEl=document.createElement('div');
  const show=async(id,trigger)=>{
    const e=(await load()).find(x=>x.id===id);if(!e)return;
    if(!sheetCtl){sheetEl.className='qc-sheet';sheetEl.hidden=true;sheetEl.innerHTML='<div class="qc-sheet-backdrop" data-close></div><section class="qc-sheet-panel" role="dialog" aria-modal="true" aria-labelledby="qc-term-title" tabindex="-1"><div class="qc-sheet-handle" aria-hidden="true"></div><header class="qc-sheet-head"><h2 id="qc-term-title"></h2><button type="button" class="qc-icon-btn" data-close aria-label="Close">'+icon('close')+'</button></header><p class="qc-term-def"></p><a class="qc-btn" data-full>OPEN IN GLOSSARY</a></section>';
      document.querySelector('.qc-shell')?.appendChild(sheetEl);sheetCtl=bottomSheet(sheetEl,{firstFocus:()=>sheetEl.querySelector('.qc-icon-btn[data-close]')})}
    sheetEl.querySelector('#qc-term-title').textContent=e.name;sheetEl.querySelector('.qc-term-def').textContent=e.def;sheetEl.querySelector('[data-full]').href='/glossary/#'+e.id;
    sheetCtl.open();
  };
  copyRoot.addEventListener('click',ev=>{const b=ev.target.closest('.qc-gterm');if(b)show(b.dataset.term,b)});
  const go=()=>load().then(link).catch(()=>{});('requestIdleCallback' in window)?requestIdleCallback(go,{timeout:1500}):setTimeout(go,300);
}

/* ── Home: term of the day. Picked from the glossary by the local calendar date, so everyone
   sees the same term on the same day; it is a static rotation, not live data. ── */
const totd=document.getElementById('qc-totd');
if(totd)glossary().then(list=>{if(!list.length)return;const d=new Date(),day=Math.floor(Date.UTC(d.getFullYear(),d.getMonth(),d.getDate())/864e5);
  const e=[...list].sort((a,b)=>a.id<b.id?-1:1)[day%list.length];
  totd.querySelector('[data-name]').textContent=e.name;totd.querySelector('[data-def]').textContent=e.def;totd.querySelector('[data-link]').href='/glossary/#'+e.id;totd.hidden=false}).catch(()=>{});

/* ── Offline page: list the pages this device has saved, so the reader knows where they can go. ── */
const saved=document.getElementById('qc-saved');
if(saved&&'caches' in window){
  const names=[['/','HOME'],['/desk/','DESKS'],['/desk/bitcoin/','BITCOIN DESK'],['/desk/dogecoin/','DOGECOIN DESK'],['/desk/xrp/','XRP DESK'],['/desk/litecoin/','LITECOIN DESK'],['/learn/','LEARN'],['/how-it-works/','HOW IT WORKS'],['/quadcom/','QUADCOM'],['/data/','DATA'],['/glossary/','GLOSSARY'],['/catalog/','CATALOG']];
  Promise.all(names.map(([u,n])=>caches.match(u,{ignoreSearch:true}).then(r=>r?[u,n]:null).catch(()=>null))).then(hits=>{
    const ok=hits.filter(Boolean);if(!ok.length)return;const ul=saved.querySelector('ul');
    for(const [u,n] of ok){const li=document.createElement('li'),a=document.createElement('a');a.href=u;a.textContent=n;li.append(a);ul.append(li)}
    saved.hidden=false});
}

/* ── Tab bar: tapping the tab you are on scrolls back to the top instead of reloading. ── */
for(const a of document.querySelectorAll('.qc-tabbar a[aria-current="page"]'))a.addEventListener('click',e=>{
  if(scrollY>0){e.preventDefault();scrollTo({top:0,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});document.getElementById('main')?.focus?.({preventScroll:true})}});

/* ── Reading progress strip under the header, only on pages longer than a screen and a half. ── */
const bar=document.querySelector('.qc-progress i');
if(bar){let q=0;const upd=()=>{q=0;const h=document.documentElement.scrollHeight-innerHeight;bar.parentElement.hidden=h<innerHeight*.5;bar.style.transform=`scaleX(${h>0?Math.min(1,scrollY/h):0})`};
  addEventListener('scroll',()=>{if(!q)q=requestAnimationFrame(upd)},{passive:true});addEventListener('resize',upd,{passive:true});upd();}
/* Back to top: shown once the reader is more than a screen and a half down, on any page length
   (a filtered glossary can grow long after load). */
{const b=document.createElement('a');b.href='#main';b.className='qc-top';b.innerHTML=icon('up')+'<span>TOP</span>';b.setAttribute('aria-label','Back to top');b.hidden=true;
 document.querySelector('.qc-shell')?.appendChild(b);
 const vis=()=>{b.hidden=scrollY<innerHeight*1.5};addEventListener('scroll',vis,{passive:true});vis();}

/* ── Catalog page: text search plus a status radiogroup (arrow keys move and select). Without
   JavaScript the controls stay hidden and every item is listed. ── */
const catBar=document.querySelector('[data-catalog-filter]');
if(catBar){
  const items=[...document.querySelectorAll('.qc-cat li')],areas=[...document.querySelectorAll('.qc-cat-area')];
  const input=catBar.querySelector('#catalogSearch'),radios=[...catBar.querySelectorAll('[role="radio"]')],count=catBar.querySelector('.qc-cat-count');
  for(const li of items)li.dataset.text=li.textContent.toLowerCase();
  let status='all';
  const apply=()=>{const q=input.value.trim().toLowerCase();let n=0;
    for(const li of items){const hit=(status==='all'||li.dataset.status===status)&&(!q||li.dataset.text.includes(q));li.hidden=!hit;if(hit)n++}
    for(const a of areas)a.hidden=!a.querySelector('li:not([hidden])');
    count.textContent=`${n} OF ${items.length} ITEMS`};
  const pick=(b,focus)=>{status=b.dataset.status;for(const r of radios){const on=r===b;r.setAttribute('aria-checked',on);r.tabIndex=on?0:-1}if(focus)b.focus();apply()};
  radios.forEach((b,i)=>{b.addEventListener('click',()=>pick(b));b.addEventListener('keydown',e=>{
    const d={ArrowRight:1,ArrowDown:1,ArrowLeft:-1,ArrowUp:-1}[e.key];if(d){e.preventDefault();pick(radios[(i+d+radios.length)%radios.length],true)}})});
  input.addEventListener('input',apply);catBar.hidden=false;pick(radios[0]);
}

/* ── Data page: what this site stores on this device, per desk (read-only, local). ── */
const storeCard=document.getElementById('qc-storage');
if(storeCard){
  const size=k=>{try{return (localStorage.getItem(k)||'').length*2}catch(_){return 0}};
  const keys=(()=>{try{return Object.keys(localStorage).filter(k=>k.startsWith('quadcom'))}catch(_){return []}})();
  const desks=[['BTC',k=>!/-(doge|xrp|ltc)(\.json)?$/.test(k)&&!/^quadcom-v(46|57)-skin$/.test(k)],['DOGE',k=>k.endsWith('-doge')],['XRP',k=>k.endsWith('-xrp')],['LTC',k=>k.endsWith('-ltc')]];
  const kb=b=>b<1024?`${b} B`:b<1048576?`${(b/1024).toFixed(1)} KB`:`${(b/1048576).toFixed(1)} MB`;
  const rows=desks.map(([n,f])=>{const ks=keys.filter(f);return `<div class="qc-metric"><span>${n} DESK · LOCAL KEYS</span><b>${ks.length?`${ks.length} · ${kb(ks.reduce((a,k)=>a+size(k),0))}`:'NONE YET'}</b></div>`}).join('');
  const out=storeCard.querySelector('[data-rows]');out.innerHTML=rows;
  navigator.storage?.estimate?.().then(e=>{if(e&&e.usage!=null)out.insertAdjacentHTML('beforeend',`<div class="qc-metric"><span>ALL SITE STORAGE (BROWSER ESTIMATE)</span><b>${kb(e.usage)}</b></div>`)}).catch(()=>{});
}

/* Service worker; a new build taking over an open page is announced, never force-reloaded. */
if('serviceWorker' in navigator){const had=!!navigator.serviceWorker.controller;
  navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).catch(()=>{});
  navigator.serviceWorker.addEventListener('controllerchange',()=>{if(had)toast('A new site build is ready',{icon:'refresh',timeout:0,action:{label:'RELOAD',run:()=>location.reload()}})});}
})();
