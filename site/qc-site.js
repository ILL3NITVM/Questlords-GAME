(()=>{'use strict';
/* Glossary: filter with a live result count, "/" to focus, Esc to clear, ?q= kept in the URL. */
const s=document.getElementById('glossarySearch'),list=document.getElementById('glossaryList'),status=document.getElementById('glossaryStatus');
if(s&&list){
  const terms=[...list.querySelectorAll('.qc-term')],total=terms.length;
  const apply=(push)=>{
    const q=s.value.trim().toLowerCase();let shown=0;
    for(const x of terms){const hit=!q||((x.dataset.term||'')+' '+x.textContent.toLowerCase()).includes(q);x.hidden=!hit;if(hit)shown++}
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
/* ── Toasts: one polite live region; newest replaces oldest beyond three. ── */
const toastRoot=document.querySelector('.qc-toasts');
const icon=n=>`<svg class="qc-ic" aria-hidden="true" focusable="false"><use href="/assets/icons.svg#i-${n}"/></svg>`;
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
/* Anchor links copy their URL when the clipboard is available; they still navigate otherwise. */
for(const a of document.querySelectorAll('.qc-anchor')){
  a.addEventListener('click',()=>{try{navigator.clipboard?.writeText(new URL(a.getAttribute('href'),location.href).href).then(()=>toast('Link copied',{icon:'link'}),()=>{})}catch(_){}});
}
/* Network state, reported only when it changes. */
addEventListener('offline',()=>toast('Offline · saved pages still open; nothing shown is live',{icon:'offline',timeout:6000}));
addEventListener('online',()=>toast('Back online',{icon:'check'}));

/* ── MORE sheet: modal bottom sheet with focus trap, Esc, backdrop and drag-to-dismiss. ── */
const sheet=document.getElementById('qc-more'),moreBtn=document.querySelector('.qc-tab-more');
if(sheet&&moreBtn){
  const panel=sheet.querySelector('.qc-sheet-panel');let lastFocus=null,hideTimer=0;
  const focusables=()=>[...panel.querySelectorAll('a[href],button:not([disabled])')].filter(el=>el.tabIndex!==-1);
  const open=()=>{clearTimeout(hideTimer);lastFocus=document.activeElement;sheet.hidden=false;document.documentElement.classList.add('qc-sheet-open');moreBtn.setAttribute('aria-expanded','true');requestAnimationFrame(()=>{sheet.classList.add('open');(panel.querySelector('a.qc-row[aria-current="page"]')||panel.querySelector('a.qc-row')||panel).focus()})};
  const close=()=>{clearTimeout(hideTimer);sheet.classList.remove('open');moreBtn.setAttribute('aria-expanded','false');document.documentElement.classList.remove('qc-sheet-open');panel.style.transform='';
    const done=()=>{sheet.hidden=true;lastFocus?.focus?.()};matchMedia('(prefers-reduced-motion: reduce)').matches?done():(hideTimer=setTimeout(done,200))};
  moreBtn.setAttribute('href','#qc-more');moreBtn.setAttribute('aria-expanded','false');
  moreBtn.addEventListener('click',e=>{e.preventDefault();sheet.hidden?open():close()});
  sheet.addEventListener('click',e=>{if(e.target.closest('[data-close]'))close()});
  sheet.addEventListener('keydown',e=>{
    if(e.key==='Escape'){e.preventDefault();close();return}
    if(e.key!=='Tab')return;const f=focusables();if(!f.length)return;const i=f.indexOf(document.activeElement);
    if(e.shiftKey&&i<=0){e.preventDefault();f[f.length-1].focus()}else if(!e.shiftKey&&i===f.length-1){e.preventDefault();f[0].focus()}
  });
  // Drag the handle or header down to dismiss.
  let y0=null;const grab=panel.querySelector('.qc-sheet-handle'),head=panel.querySelector('.qc-sheet-head');
  for(const el of [grab,head])el?.addEventListener('pointerdown',e=>{if(e.target.closest('button'))return;y0=e.clientY;panel.setPointerCapture?.(e.pointerId);panel.classList.add('dragging')});
  panel.addEventListener('pointermove',e=>{if(y0===null)return;panel.style.transform=`translateY(${Math.max(0,e.clientY-y0)}px)`});
  const end=e=>{if(y0===null)return;const d=e.clientY-y0;y0=null;panel.classList.remove('dragging');if(d>80)close();else panel.style.transform=''};
  panel.addEventListener('pointerup',end);panel.addEventListener('pointercancel',end);
  /* Skin segmented control: shares the desk's preference key. */
  const KEY='quadcom-v46-skin',seg=[...panel.querySelectorAll('[data-skin]')];
  const cur=()=>{try{return localStorage.getItem(KEY)==='off'?'off':'regalia'}catch(_){return 'regalia'}};
  const paint=()=>{const c=cur();for(const b of seg){const on=b.dataset.skin===c;b.setAttribute('aria-checked',String(on));b.tabIndex=on?0:-1}};
  for(const b of seg)b.addEventListener('click',()=>{const v=b.dataset.skin;try{let prev=localStorage.getItem(KEY);localStorage.setItem(KEY,v==='off'?'off':(prev&&prev!=='off'?prev:'regalia'))}catch(_){}
    document.documentElement.dataset.qcTexture=v==='off'?'off':'regalia';paint();toast(v==='off'?'Skin off':'REGALIA skin on',{icon:'skin'})});
  panel.querySelector('.qc-seg')?.addEventListener('keydown',e=>{if(!/Arrow(Left|Right)/.test(e.key))return;e.preventDefault();const i=seg.findIndex(b=>b.getAttribute('aria-checked')==='true');const n=seg[(i+(e.key==='ArrowRight'?1:seg.length-1))%seg.length];n.click();n.focus()});
  paint();
}

/* ── Reading progress strip under the header, only on pages longer than a screen and a half. ── */
const bar=document.querySelector('.qc-progress i');
if(bar){let q=0;const upd=()=>{q=0;const h=document.documentElement.scrollHeight-innerHeight;bar.parentElement.hidden=h<innerHeight*.5;bar.style.transform=`scaleX(${h>0?Math.min(1,scrollY/h):0})`};
  addEventListener('scroll',()=>{if(!q)q=requestAnimationFrame(upd)},{passive:true});addEventListener('resize',upd,{passive:true});upd();}
/* Back to top: shown once the reader is more than a screen and a half down, on any page length
   (a filtered glossary can grow long after load). */
{const b=document.createElement('a');b.href='#main';b.className='qc-top';b.innerHTML=icon('up')+'<span>TOP</span>';b.setAttribute('aria-label','Back to top');b.hidden=true;
 document.querySelector('.qc-shell')?.appendChild(b);
 const vis=()=>{b.hidden=scrollY<innerHeight*1.5};addEventListener('scroll',vis,{passive:true});vis();}
/* Service worker; a new build taking over an open page is announced, never force-reloaded. */
if('serviceWorker' in navigator){const had=!!navigator.serviceWorker.controller;
  navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).catch(()=>{});
  navigator.serviceWorker.addEventListener('controllerchange',()=>{if(had)toast('A new site build is ready',{icon:'refresh',timeout:0,action:{label:'RELOAD',run:()=>location.reload()}})});}
})();
