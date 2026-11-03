/* File controls and saves remain native forms when JavaScript is unavailable. */
(() => {
    const previews = new Map();
    const clearPreviews = () => {
        previews.forEach(value => URL.revokeObjectURL(value.url));
        previews.clear();
    };
    document.addEventListener('culturelink:page-ready', clearPreviews);
    window.addEventListener('pagehide', clearPreviews);
    document.addEventListener('change', event => {
        if (!event.target.matches('[data-photo-input]')) return;
        const input = event.target;
        const field = input.closest('[data-photo-field]');
        const preview = field.querySelector('[data-photo-preview]');
        const status = field.querySelector('[data-photo-status]');
        const previous = previews.get(input);
        if (previous) {
            URL.revokeObjectURL(previous.url);
            preview.innerHTML = previous.original;
            previews.delete(input);
        }
        input.setCustomValidity('');
        status.textContent = '';
        const file = input.files[0];
        if (!file) return;
        if (file.size > 5 * 1024 * 1024) {
            input.setCustomValidity('Choose a picture smaller than 5 MB.');
            status.textContent = input.validationMessage;
            input.reportValidity();
            return;
        }
        const url = URL.createObjectURL(file);
        const original = preview.innerHTML;
        previews.set(input, {url, original});
        const image = document.createElement('img');
        image.alt = 'Selected picture preview';
        image.onload = () => { status.textContent = 'Picture selected. Save your profile to keep it.'; };
        image.onerror = () => {
            if (previews.get(input)?.url !== url) return;
            URL.revokeObjectURL(url);
            previews.delete(input);
            preview.innerHTML = original;
            input.setCustomValidity('Choose a readable PNG, JPG, or WebP picture.');
            status.textContent = input.validationMessage;
        };
        const picture = preview.querySelector('.profile-picture');
        picture.replaceChildren(image);
        image.src = url;
        const remove = field.querySelector('[data-photo-remove]');
        if (remove) remove.checked = false;
    });
})();
