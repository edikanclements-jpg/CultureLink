/* Setup stays on one document; every form still works without JavaScript. */
(() => {
    document.documentElement.classList.add('setup-motion');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const easing = 'cubic-bezier(.22, 1, .36, 1)';
    let busy = false;
    let usedSoftNavigation = Boolean(window.history.state?.culturelinkSetup);

    const animate = async (element, frames, duration = 240) => {
        if (!element || reducedMotion.matches || typeof element.animate !== 'function') return;
        const animation = element.animate(frames, {duration, easing});
        // Cancellation (for example, leaving the page) must not block setup.
        await animation.finished.catch(() => {});
    };

    const openRoleDialog = dialog => {
        if (!dialog || typeof dialog.showModal !== 'function') return;
        if (dialog.open) dialog.close();
        dialog.showModal();
        const heading = dialog.querySelector('.auth-errors') || dialog.querySelector('#role-heading');
        if (heading) heading.focus({preventScroll: true});
    };

    const prepareRoleDialog = () => {
        const dialog = document.querySelector('[data-role-dialog]');
        if (!dialog || dialog.dataset.dialogReady) return;
        dialog.dataset.dialogReady = 'true';
        document.querySelectorAll('[data-open-role]').forEach(button => {
            button.addEventListener('click', () => openRoleDialog(dialog));
        });
        dialog.addEventListener('cancel', async event => {
            event.preventDefault();
            if (busy) return;
            await animate(dialog, [
                {opacity: 1, transform: 'translateY(0) scale(1)'},
                {opacity: 0, transform: 'translateY(10px) scale(.98)'}
            ], 160);
            dialog.close();
            document.querySelector('[data-open-role]')?.focus({preventScroll: true});
        });
        openRoleDialog(dialog);
    };

    prepareRoleDialog();
    if (typeof window.fetch !== 'function' || typeof window.FormData !== 'function') return;

    const setPending = (form, submitter) => {
        const buttons = [...form.querySelectorAll('button[type="submit"]')];
        const original = buttons.map(button => ({button, html: button.innerHTML, disabled: button.disabled}));
        form.setAttribute('aria-busy', 'true');
        buttons.forEach(button => { button.disabled = true; });
        const roleChoice = form.dataset.onboardingForm === 'role';
        if (roleChoice) {
            buttons.forEach(button => button.classList.add(button === submitter ? 'is-selected' : 'is-unselected'));
            const action = submitter?.querySelector('.role-card-action');
            if (action) action.textContent = 'Opening your profile…';
            const announcement = form.querySelector('[data-setup-announcement]');
            if (announcement) announcement.textContent = 'Opening your ' + submitter.value + ' profile.';
        } else if (submitter) {
            submitter.textContent = form.dataset.onboardingForm === 'register' ? 'Creating your account…' : 'Saving your profile…';
            submitter.classList.add('setup-loading');
        }
        return () => {
            form.removeAttribute('aria-busy');
            original.forEach(({button, html, disabled}) => {
                button.innerHTML = html;
                button.disabled = disabled;
                button.classList.remove('is-selected', 'is-unselected', 'setup-loading');
            });
            const announcement = form.querySelector('[data-setup-announcement]');
            if (announcement) announcement.textContent = '';
        };
    };

    const showRecovery = form => {
        const notice = document.createElement('div');
        notice.className = 'auth-errors';
        notice.dataset.onboardingFeedback = '';
        notice.setAttribute('role', 'alert');
        notice.tabIndex = -1;
        const message = document.createElement('p');
        message.textContent = "We couldn't load the next step. Your progress may already be saved.";
        const link = document.createElement('a');
        link.href = form.dataset.setupRecovery;
        link.textContent = 'Continue setup from My Account';
        notice.append(message, link);
        form.prepend(notice);
        notice.focus();
    };

    const renderStep = async (parsed, url, step) => {
        const currentMain = document.getElementById('main-content');
        const nextMain = document.importNode(parsed.getElementById('main-content'), true);
        const nextHeader = parsed.querySelector('.site-header');
        const dialog = currentMain.querySelector('[data-role-dialog]');
        const leaving = dialog?.open ? dialog : currentMain;
        await animate(leaving, [
            {opacity: 1, transform: 'translateY(0) scale(1)'},
            {opacity: 0, transform: 'translateY(-8px) scale(.99)'}
        ], 150);

        // The new dialog is opened modally only after it joins this document.
        nextMain.querySelector('[data-role-dialog]')?.removeAttribute('open');
        if (dialog?.open && typeof dialog.close === 'function') dialog.close();
        currentMain.replaceWith(nextMain);
        if (nextHeader) document.querySelector('.site-header').replaceWith(document.importNode(nextHeader, true));
        document.title = parsed.title;
        const state = {culturelinkSetup: true};
        if (step === 'register' || url.href === window.location.href) history.replaceState(state, '', url);
        else history.pushState(state, '', url);
        usedSoftNavigation = true;
        window.scrollTo(0, 0);
        document.dispatchEvent(new Event('culturelink:page-ready'));
        prepareRoleDialog();

        if (!nextMain.querySelector('[data-role-dialog]')) {
            const content = nextMain.querySelector('.profile-shell, .auth-layout, .account-summary') || nextMain;
            const focusTarget = nextMain.querySelector('.auth-errors') || nextMain.querySelector('h1, h2');
            if (focusTarget) {
                focusTarget.tabIndex = -1;
                focusTarget.focus({preventScroll: true});
            }
            void animate(content, [
                {opacity: 0, transform: 'translateY(16px)'},
                {opacity: 1, transform: 'translateY(0)'}
            ], 360);
        }
    };

    document.addEventListener('submit', async event => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || !form.matches('[data-onboarding-form]') || event.defaultPrevented) return;
        const action = new URL(form.action, window.location.href);
        if (action.origin !== window.location.origin) return;
        event.preventDefault();
        if (busy) return;
        busy = true;
        form.querySelector('[data-onboarding-feedback]')?.remove();
        const submitter = event.submitter || form.querySelector('button[type="submit"]');
        // Capture the selected role before disabling the submit buttons.
        const body = new FormData(form);
        if (submitter?.name) body.append(submitter.name, submitter.value);
        const restore = setPending(form, submitter);
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 20000);
        try {
            const response = await fetch(action, {
                method: 'POST', body, credentials: 'same-origin',
                headers: {'Accept': 'text/html'}, signal: controller.signal, cache: 'no-store'
            });
            const url = new URL(response.url);
            if (url.origin !== window.location.origin || !response.headers.get('content-type')?.includes('text/html')) throw new Error('Unexpected setup response');
            const parsed = new DOMParser().parseFromString(await response.text(), 'text/html');
            if (!parsed.getElementById('main-content')) throw new Error('Missing setup page');
            window.clearTimeout(timeout);
            await renderStep(parsed, url, form.dataset.onboardingForm);
        } catch {
            // Never repeat a POST automatically: the first one may have saved.
            if (form.isConnected) {
                restore();
                showRecovery(form);
            }
        } finally {
            window.clearTimeout(timeout);
            busy = false;
        }
    });

    // Back/Forward resolves the server's current account state, without
    // caching a password form or another user's account page in history.
    window.addEventListener('popstate', event => {
        if (usedSoftNavigation || event.state?.culturelinkSetup) window.location.reload();
    });
})();
