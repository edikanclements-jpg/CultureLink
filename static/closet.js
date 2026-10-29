/* Save/remove progressively; the same CSRF-protected forms work without JS. */
(() => {
    if (typeof window.fetch !== 'function') return;
    const pending = new Set();
    let feedbackTimer;

    const announce = message => {
        const feedback = document.querySelector('[data-closet-feedback]');
        if (!feedback) return;
        window.clearTimeout(feedbackTimer);
        feedback.textContent = message;
        feedback.hidden = false;
        feedbackTimer = window.setTimeout(() => { feedback.hidden = true; }, 6000);
    };

    const reflect = (forms, result) => {
        forms.forEach(form => {
            const button = form.querySelector('[data-closet-button]');
            const removeMode = form.dataset.closetMode === 'remove';
            form.action = result.saved ? form.dataset.removeUrl : form.dataset.saveUrl;
            button.classList.toggle('is-saved', result.saved);
            if (!removeMode) button.setAttribute('aria-pressed', String(result.saved));
            form.querySelector('[data-closet-label]').textContent = removeMode ? 'Remove' : result.saved ? 'Saved' : 'Save';
        });
        document.querySelectorAll('[data-closet-count]').forEach(counter => {
            const number = document.createElement('strong');
            number.textContent = result.count;
            counter.replaceChildren(number, document.createTextNode(' saved ' + (result.count === 1 ? 'piece' : 'pieces')));
        });
    };

    document.addEventListener('submit', async event => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || !form.matches('[data-closet-form]') || event.defaultPrevented) return;
        const action = new URL(form.action, window.location.href);
        if (action.origin !== window.location.origin) return;
        event.preventDefault();
        const id = form.dataset.productId;
        if (!/^[0-9]+$/.test(id) || pending.has(id)) return;
        pending.add(id);
        const forms = [...document.querySelectorAll('[data-closet-form]')].filter(item => item.dataset.productId === id);
        const originals = forms.map(item => {
            const button = item.querySelector('[data-closet-button]');
            const label = item.querySelector('[data-closet-label]');
            const original = {button, label, text: label.textContent, disabled: button.disabled};
            button.disabled = true;
            button.setAttribute('aria-busy', 'true');
            label.textContent = action.pathname.endsWith('/save') ? 'Saving…' : 'Removing…';
            return original;
        });
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 20000);
        let confirmed = false;
        try {
            const response = await fetch(action, {
                method: 'POST', body: new FormData(form), credentials: 'same-origin',
                headers: {'Accept': 'application/json'}, signal: controller.signal, cache: 'no-store'
            });
            if (!response.headers.get('content-type')?.includes('application/json')) {
                throw new Error(response.status === 400 ? 'Please refresh the page and try saving again.' : 'We couldn’t confirm the change. Refresh the page to check your closet.');
            }
            const result = await response.json();
            if (!response.ok) {
                if (result.redirect) {
                    const destination = new URL(result.redirect, window.location.href);
                    if (destination.origin === window.location.origin && ['/login', '/onboarding/role'].includes(destination.pathname)) {
                        window.location.assign(destination);
                        return;
                    }
                }
                throw new Error(result.error || 'We couldn’t update your closet. Please try again.');
            }
            if (result.product_id !== Number(id) || typeof result.saved !== 'boolean' || !Number.isInteger(result.count) || result.count < 0) throw new Error('Please refresh the page to check your closet.');
            confirmed = true;
            reflect(forms, result);
            document.dispatchEvent(new CustomEvent('culturelink:closet-change', {detail: result}));
            const grid = document.querySelector('[data-closet-grid]');
            if (grid && !result.saved) {
                const card = form.closest('.product-card');
                const cards = [...grid.querySelectorAll('.product-card')];
                const index = cards.indexOf(card);
                const next = cards[index + 1] || cards[index - 1];
                if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches && typeof card.animate === 'function') {
                    await card.animate([{opacity: 1}, {opacity: 0, transform: 'translateY(5px)'}], {duration: 150}).finished.catch(() => {});
                }
                card.remove();
                const remaining = grid.querySelectorAll('.product-card').length;
                if (remaining !== result.count) {
                    window.location.reload();
                    return;
                }
                grid.hidden = remaining === 0;
                document.querySelector('[data-closet-empty]').hidden = remaining !== 0;
                const focusTarget = next?.querySelector('[data-closet-button]') || document.querySelector('[data-closet-empty] a');
                focusTarget?.focus({preventScroll: true});
            }
            announce(result.saved ? 'Saved ' + form.dataset.productName + ' to your closet.' : 'Removed ' + form.dataset.productName + ' from your closet.');
        } catch (error) {
            announce(error.name === 'AbortError' || error instanceof TypeError ? 'We couldn’t confirm the change. Refresh the page to check your closet.' : error.message);
        } finally {
            window.clearTimeout(timeout);
            originals.forEach(({button, label, text, disabled}) => {
                button.disabled = disabled;
                button.removeAttribute('aria-busy');
                if (!confirmed) label.textContent = text;
            });
            pending.delete(id);
        }
    });
})();
