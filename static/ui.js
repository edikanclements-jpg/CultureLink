// Keep Discover filters collapsible on phones without losing their form values.
(() => {
    const panel = document.querySelector('.filter-panel');
    if (!panel) return;
    const smallScreen = window.matchMedia('(max-width: 900px)');
    const updatePanel = () => { panel.open = !smallScreen.matches; };
    updatePanel();
    smallScreen.addEventListener('change', updatePanel);
})();
