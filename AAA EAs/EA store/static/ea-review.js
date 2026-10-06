(() => {
  const rows=[...document.querySelectorAll('[data-review-phase]')];
  const search=document.querySelector('#review-search');
  const phase=document.querySelector('#review-phase');
  const loadedPhase=new URL(location.href).searchParams.get('phase')||'all';
  function apply(){let visible=0;for(const row of rows){const show=(!search?.value||row.dataset.reviewSearch.includes(search.value.trim().toLowerCase()))&&(!phase||phase.value==='all'||row.dataset.reviewPhase===phase.value);row.hidden=!show;if(show)visible++}const counter=document.querySelector('#review-visible-count');if(counter)counter.textContent=visible+' of 37 EAs shown';for(const link of document.querySelectorAll('[data-phase-link]')){const active=link.dataset.phaseLink===phase.value;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current')}}
  search?.addEventListener('input',apply);phase?.addEventListener('change',()=>{
    // A server-filtered page does not contain other phases: fetch the new scope.
    if(loadedPhase!=='all'&&phase.value!==loadedPhase){const url=new URL(location.href);url.searchParams.set('phase',phase.value);url.searchParams.set('q',search.value.trim());location.assign(url.href);return}
    apply();
  });
})();
