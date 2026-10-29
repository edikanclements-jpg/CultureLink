/* Same native forms, enhanced with a single in-flight search and safe HTML swaps. */
(() => {
  'use strict';
  if (!window.fetch || !document.querySelector('[data-guide-body]')) return;
  let pending = false;
  document.addEventListener('keydown', event => {
    if (event.target.id === 'guide-query' && event.key === 'Enter' && !event.shiftKey && !event.ctrlKey && !event.metaKey && !event.altKey && !event.isComposing) {
      event.preventDefault();
      if (!pending) event.target.form.requestSubmit(event.target.form.querySelector('[data-guide-send]'));
    }
  });
  document.addEventListener('submit', async event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.matches('[data-guide-form]') || event.defaultPrevented) return;
    const url = new URL(form.action, location.href);
    if (url.origin !== location.origin) return;
    event.preventDefault();
    if (pending) return;
    const body = new FormData(form);
    if (event.submitter?.name) body.append(event.submitter.name, event.submitter.value);
    pending = true;
    const root = document.querySelector('[data-guide-body]');
    const status = document.querySelector('[data-guide-status]');
    const buttons = [...root.querySelectorAll('[data-guide-form] button')].map(button => ({button,disabled:button.disabled}));
    const textarea = root.querySelector('#guide-query');
    buttons.forEach(({button}) => {button.disabled=true;});
    if (textarea) textarea.readOnly=true;
    root.setAttribute('aria-busy','true');
    status.hidden=false;
    status.textContent=form.action.endsWith('/reset')?'Starting a new search...':'Searching the catalog...';
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),22000);
    try {
      const response=await fetch(url,{method:'POST',body,credentials:'same-origin',cache:'no-store',signal:controller.signal,headers:{Accept:'text/html'}});
      const destination=new URL(response.url);
      if (destination.origin===location.origin&&['/login','/onboarding/role'].includes(destination.pathname)) {
        location.assign(destination.href);return;
      }
      if (!response.headers.get('content-type')?.includes('text/html')||(!response.ok&&![400,429,503].includes(response.status))) throw new Error();
      const parsed=new DOMParser().parseFromString(await response.text(),'text/html');
      const next=parsed.querySelector('[data-guide-body]');
      if (!next) throw new Error();
      root.replaceWith(next);
      const target=next.querySelector('[data-guide-error]')||next.querySelector('[data-guide-reply]');
      target?.focus({preventScroll:true});
      if (target) target.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
      status.hidden=true;
    } catch (_) {
      status.textContent="We couldn't confirm that search. Your text is still here. Refresh to check your last result, or try again.";
    } finally {
      clearTimeout(timeout);
      root.removeAttribute('aria-busy');
      buttons.forEach(({button,disabled})=>{button.disabled=disabled;});
      if (textarea) textarea.readOnly=false;
      pending=false;
    }
  });
})();
