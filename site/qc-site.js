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
  addEventListener('hashchange',()=>{const t=document.getElementById(location.hash.slice(1));if(t&&t.hidden){s.value='';apply(true);t.scrollIntoView()}});
  apply(false);
}
/* Anchor links copy their URL when the clipboard is available; they still navigate otherwise. */
for(const a of document.querySelectorAll('.qc-anchor')){
  a.addEventListener('click',()=>{try{navigator.clipboard?.writeText(new URL(a.getAttribute('href'),location.href).href).then(()=>{a.dataset.copied='1';setTimeout(()=>delete a.dataset.copied,1200)},()=>{})}catch(_){}});
}
/* Back to top on long pages. */
if(document.documentElement.scrollHeight>innerHeight*2.2){
  const b=document.createElement('a');b.href='#main';b.className='qc-top';b.textContent='↑ TOP';b.setAttribute('aria-label','Back to top');document.querySelector('.qc-shell')?.appendChild(b);
}
if('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).catch(()=>{});
})();
