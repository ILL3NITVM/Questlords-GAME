
(()=>{'use strict';
const s=document.getElementById('glossarySearch'),list=document.getElementById('glossaryList');
if(s&&list){s.addEventListener('input',()=>{const q=s.value.trim().toLowerCase();list.querySelectorAll('.qc-term').forEach(x=>x.hidden=q&&!((x.dataset.term||'')+' '+x.textContent.toLowerCase()).includes(q));});}
if('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).catch(()=>{});
})();
