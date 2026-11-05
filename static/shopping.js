/* Enhance the native Assistant forms with a conversation and a reply reveal. */
(() => {
    if (!window.fetch || !document.querySelector('[data-guide-body]')) return;
    let pending = false;

    function revealReply(reply) {
        const text = reply?.querySelector('[data-assistant-text]');
        if (!text || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        const parts = text.textContent.split(/(\s+)/);
        const wordCount = parts.filter(part => /\S/.test(part)).length;
        let index = 0;
        text.replaceChildren(...parts.map(part => {
            if (!/\S/.test(part)) return document.createTextNode(part);
            const word = document.createElement('span');
            word.className = 'assistant-reveal-word';
            word.textContent = part;
            word.style.setProperty('--reveal-delay', Math.round(index++ * Math.min(37, 870 / wordCount)) + 'ms');
            return word;
        }));
    }

    function previousTurn(turn) {
        const user = turn.querySelector('.assistant-user');
        const answer = turn.querySelector('[data-assistant-text]');
        if (!user || !answer) return null;
        const summary = document.createElement('div');
        summary.className = 'assistant-past';
        const reply = document.createElement('p');
        const speaker = document.createElement('strong');
        speaker.textContent = 'Assistant: ';
        reply.append(speaker, document.createTextNode(answer.textContent));
        summary.append(user.cloneNode(true), reply);
        return summary;
    }

    function restoreConversation(before, after) {
        const history = [...before.querySelector('[data-assistant-history]').children];
        const turn = before.querySelector('[data-assistant-turn]');
        const previous = turn && previousTurn(turn);
        if (after.querySelector('[data-guide-error]')) {
            if (turn) after.querySelector('[data-assistant-pending]').before(turn);
        } else if (previous) {
            history.push(previous);
        }
        after.querySelector('[data-assistant-history]').append(...history.slice(-3));
    }

    document.addEventListener('keydown', event => {
        if (event.target.id !== 'guide-query' || event.key !== 'Enter' || event.shiftKey || event.ctrlKey
            || event.metaKey || event.altKey || event.isComposing) return;
        event.preventDefault();
        if (!pending) event.target.form.requestSubmit(event.target.form.querySelector('[data-guide-send]'));
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
        const reset = url.pathname.endsWith('/reset');
        const root = document.querySelector('[data-guide-body]');
        const progress = root.querySelector('[data-assistant-pending]');
        const thinking = progress.querySelector('[data-thinking-text]');
        const question = String(body.get('example') || body.get('query') || '').trim();
        const buttons = [...root.querySelectorAll('[data-guide-form] button')];
        const enabled = buttons.filter(button => !button.disabled);
        const textarea = root.querySelector('#guide-query');
        pending = true;
        enabled.forEach(button => { button.disabled = true; });
        textarea.readOnly = true;
        progress.querySelector('[data-pending-question]').textContent = question;
        progress.querySelector('[data-pending-user]').hidden = !question;
        progress.hidden = false;
        thinking.textContent = reset ? 'Starting a new chat…' : 'Looking through the catalog…';
        const motion = matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
        if (!reset) progress.scrollIntoView({block:'nearest', behavior:motion});

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 22000);
        try {
            const response = await fetch(url, {
                method:'POST', body, credentials:'same-origin', cache:'no-store',
                signal:controller.signal, headers:{Accept:'text/html'}
            });
            const destination = new URL(response.url);
            if (destination.origin === location.origin && ['/login','/onboarding/role'].includes(destination.pathname)) {
                location.assign(destination.href);
                return;
            }
            if (!response.headers.get('content-type')?.includes('text/html') ||
                (!response.ok && ![400,429,503].includes(response.status))) throw new Error();
            const parsed = new DOMParser().parseFromString(await response.text(), 'text/html');
            const next = parsed.querySelector('[data-guide-body]');
            if (!next) throw new Error();
            if (!reset) restoreConversation(root, next);
            root.replaceWith(next);
            const target = next.querySelector('[data-guide-error]') || next.querySelector('[data-guide-reply]');
            if (response.ok && !reset) revealReply(target);
            if (target) {
                target.focus({preventScroll:true});
                target.scrollIntoView({block:'start', behavior:motion});
            } else {
                next.querySelector('#guide-query').focus();
            }
        } catch (_) {
            progress.querySelector('[data-pending-user]').hidden = true;
            thinking.textContent = "We couldn't confirm that search. Try again or refresh to check your latest result.";
        } finally {
            clearTimeout(timeout);
            enabled.forEach(button => { button.disabled = false; });
            textarea.readOnly = false;
            pending = false;
        }
    });
})();
