/* Native menu disclosure with keyboard dismissal and outside-click closing. */
(() => {
    document.addEventListener('click', event => {
        const menu = document.querySelector('[data-site-menu][open]');
        if (menu && !menu.contains(event.target)) menu.open = false;
    });
    document.addEventListener('keydown', event => {
        if (event.key !== 'Escape' || event.defaultPrevented) return;
        const menu = document.querySelector('[data-site-menu][open]');
        if (!menu) return;
        const restoreFocus = menu.contains(document.activeElement);
        menu.open = false;
        if (restoreFocus) menu.querySelector('summary').focus({preventScroll: true});
    });
})();
