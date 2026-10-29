/* Re-initialize controls when setup replaces a page without a full reload. */
(() => {
    const prepareAccountForms = () => {
        const errors = document.querySelector('.auth-errors');
        if (errors) errors.focus({preventScroll: true});
        document.querySelectorAll('[data-password-toggle]').forEach(button => {
            const input = document.getElementById(button.dataset.passwordToggle);
            if (!input || button.dataset.toggleReady) return;
            button.dataset.toggleReady = 'true';
            button.hidden = false;
            const label = button.getAttribute('aria-label') || 'Show password';
            button.addEventListener('click', () => {
                const show = input.type === 'password';
                input.type = show ? 'text' : 'password';
                button.textContent = show ? 'Hide' : 'Show';
                button.setAttribute('aria-pressed', String(show));
                button.setAttribute('aria-label', show ? label.replace('Show', 'Hide') : label);
            });
        });
    };
    prepareAccountForms();
    document.addEventListener('culturelink:page-ready', prepareAccountForms);
})();
