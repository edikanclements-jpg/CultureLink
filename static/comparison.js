/* Existing POST forms remain the fallback when scripts are unavailable. */
(() => {
    if (typeof fetch !== 'function') return;
    let selected = [];
    let busy = false;
    const panel = document.querySelector('[data-compare-panel]');
    if (panel) {
        try { selected = JSON.parse(panel.dataset.selected); } catch { return; }
    }
    const announce = message => {
        const status = document.querySelector('[data-closet-feedback]');
        if (status) { status.textContent = message; status.hidden = false; }
    };
    const render = () => {
        document.querySelectorAll('[data-compare-toggle]').forEach(button => {
            const form = button.form;
            const chosen = selected.includes(Number(form.dataset.productId));
            form.action = chosen ? form.dataset.removeUrl : form.dataset.addUrl;
            button.classList.toggle('is-selected', chosen);
            button.setAttribute('aria-pressed', String(chosen));
            button.disabled = busy || (!chosen && selected.length >= 3);
            form.querySelector('[data-compare-label]').textContent = chosen ? 'Added to Compare' : 'Compare';
            button.lastElementChild.textContent = chosen ? '✓' : '+';
        });
        const count = document.querySelector('[data-compare-count]');
        if (count) count.textContent = selected.length + ' of 3 selected';
        document.querySelectorAll('[data-compare-open]').forEach(button => { button.disabled = busy || selected.length < 2; });
        document.querySelectorAll('[data-compare-clear] button').forEach(button => { button.disabled = busy || selected.length === 0; });
    };
    document.addEventListener('culturelink:closet-change', event => {
        if (!event.detail.saved) {
            selected = selected.filter(id => id !== event.detail.product_id);
            render();
        }
    });
    document.addEventListener('submit', async event => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || !form.matches('[data-compare-form]') || event.defaultPrevented) return;
        if (new URL(form.action).origin !== location.origin) return;
        event.preventDefault();
        if (busy) return;
        busy = true;
        render();
        form.setAttribute('aria-busy', 'true');
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 20000);
        try {
            const response = await fetch(form.action, {method: 'POST', body: new FormData(form), credentials: 'same-origin', headers: {'Accept': 'application/json'}, signal: controller.signal, cache: 'no-store'});
            if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('Please refresh the page and try again.');
            const result = await response.json();
            if (!response.ok) {
                if (result.redirect) {
                    const destination = new URL(result.redirect, location.href);
                    if (destination.origin === location.origin && ['/login','/onboarding/role'].includes(destination.pathname)) { location.assign(destination); return; }
                }
                throw new Error(result.error || 'We couldn’t update your comparison. Please try again.');
            }
            if (!Array.isArray(result.selected) || result.selected.length > 3 || !result.selected.every(Number.isInteger)) throw new Error('Please refresh the page to check your comparison.');
            if (document.querySelector('[data-comparison-page]')) { location.reload(); return; }
            selected = result.selected.filter(id => document.querySelector('[data-compare-form][data-product-id="' + id + '"]'));
            announce(selected.length + ' of 3 pieces selected for comparison.');
        } catch (error) {
            announce(error.name === 'AbortError' || error instanceof TypeError ? 'We couldn’t confirm the change. Refresh the page to check your comparison.' : error.message);
        } finally {
            clearTimeout(timeout);
            form.removeAttribute('aria-busy');
            busy = false;
            render();
        }
    });
    render();
})();
