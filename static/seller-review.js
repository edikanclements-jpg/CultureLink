/* Native forms and server validation also work without this enhancement. */
(() => {
    const submitted = document.querySelector('[data-submitted-dialog]');
    if (submitted) {
        const continueLink = submitted.querySelector('[data-continue-setup]');
        if (typeof submitted.showModal === 'function') {
            if (submitted.open) submitted.close();
            submitted.showModal();
            submitted.setAttribute('aria-modal', 'true');
        }
        // Dismissing the only panel would leave the visitor on an empty page.
        submitted.addEventListener('cancel', event => {
            event.preventDefault();
            continueLink.focus();
        });
        continueLink.focus();
    }
    const update = form => {
        const select = form.querySelector('[data-piece-size-mode]');
        const fields = form.querySelector('[data-standard-piece-fields]');
        if (!select || !fields) return;
        const custom = select.value === 'custom';
        fields.hidden = custom;
        fields.querySelectorAll('input, select').forEach(input => { input.disabled = custom; });
        form.querySelector('[data-custom-price-help]').hidden = !custom;
    };
    const prepare = () => document.querySelectorAll('[data-seller-piece-form]').forEach(update);
    document.addEventListener('change', event => {
        if (event.target.matches('[data-piece-size-mode]')) update(event.target.form);
    });
    document.addEventListener('culturelink:page-ready', prepare);
    prepare();
})();
