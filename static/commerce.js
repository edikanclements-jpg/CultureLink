/* Immediate cart count updates; ordinary form navigation works without JS. */
(() => {
    const cart=()=>document.querySelector('[data-cart-icon]');
    let timer;
    const update=count=>{
        const icon=cart();
        if(!icon||!Number.isSafeInteger(count)||count<0)return;
        const badge=icon.querySelector('[data-cart-count]');
        const changed=badge.textContent!==String(count);
        badge.textContent=String(count);
        icon.setAttribute('aria-label',`Cart, ${count} ${count===1?'piece':'pieces'}`);
        if(changed){icon.classList.remove('cart-just-updated');void icon.offsetWidth;icon.classList.add('cart-just-updated');}
    };
    const notify=message=>{
        const panel=document.querySelector('[data-cart-feedback]');if(!panel)return;
        clearTimeout(timer);panel.replaceChildren(document.createTextNode(message+' '));
        if(cart()){const link=document.createElement('a');link.href=cart().href;link.textContent='View cart';panel.append(link);}
        panel.hidden=false;timer=setTimeout(()=>{panel.hidden=true;},6500);
    };
    const refresh=async()=>{
        const icon=cart();if(!icon||document.visibilityState==='hidden')return;
        try{
            const r=await fetch(icon.dataset.countUrl,{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}});
            if(r.ok&&r.headers.get('content-type')?.includes('application/json'))update((await r.json()).count);
        }catch(_){/* Keep the count already rendered by the server. */}
    };
    document.addEventListener('submit',async event=>{
        const form=event.target;
        if(!(form instanceof HTMLFormElement)||!form.matches('[data-cart-add]')||event.defaultPrevented)return;
        event.preventDefault();if(form.dataset.saving==='true')return;form.dataset.saving='true';
        const button=event.submitter||form.querySelector('button[type="submit"]');
        const previous=button.textContent;const body=new FormData(form);button.disabled=true;button.textContent='Adding…';
        try{
            const response=await fetch(form.action,{method:'POST',body,credentials:'same-origin',headers:{Accept:'application/json'}});
            if(!response.headers.get('content-type')?.includes('application/json'))throw new Error('unconfirmed');
            const data=await response.json();
            if(!response.ok){notify(data.error||'Check your cart before trying again.');return;}
            update(data.count);notify(data.message||'Your piece is in the cart.');
            const picker=form.closest('.card-size-picker');
            if(picker){picker.open=false;picker.querySelector('summary').focus({preventScroll:true});}
            const next=form.parentElement.querySelector('[data-cart-next]');if(next)next.hidden=false;
        }catch(_){notify("We couldn't confirm the update. Check your cart before trying again.");await refresh();}
        finally{button.disabled=false;button.textContent=previous;delete form.dataset.saving;}
    });
    window.addEventListener('pageshow',refresh);document.addEventListener('visibilitychange',refresh);
})();
