/* Native disclosures remain available without JavaScript or Popover support. */
(() => {
    'use strict';
    if (typeof HTMLElement.prototype.showPopover !== 'function') return;
    let active = null;
    let frame = 0;
    let pointerFocus = false;
    // Let a pointer click finish before opening. Opening on touch-generated
    // focus can move the panel between pointerdown and click on a phone.
    document.addEventListener('pointerdown', () => { pointerFocus = true; }, true);
    document.addEventListener('click', () => { pointerFocus = false; }, true);
    document.addEventListener('keydown', () => { pointerFocus = false; }, true);
    document.addEventListener('pointercancel', () => { pointerFocus = false; }, true);

    function place(state) {
        if (!state.root.open || !state.panel.matches(':popover-open')) return;
        const anchor = state.trigger.getBoundingClientRect();
        const panel = state.panel.getBoundingClientRect();
        const margin = 16;
        const width = document.documentElement.clientWidth;
        const height = window.innerHeight;
        const below = height - anchor.bottom - margin - 10;
        const above = anchor.top - margin - 10;
        const preferred = panel.height <= below || below >= above ? anchor.bottom + 10 : anchor.top - panel.height - 10;
        const left = Math.max(margin, Math.min(anchor.left, width - panel.width - margin));
        const top = Math.max(margin, Math.min(preferred, height - panel.height - margin));
        state.panel.style.left = left + 'px';
        state.panel.style.top = top + 'px';
    }

    function hasFocus(state) { return state.root.contains(document.activeElement); }

    function close(state, restoreFocus = false) {
        clearTimeout(state.closeTimer);
        state.pinned = false;
        state.dismissed = hasFocus(state);
        state.suppressFocus = true;
        if (restoreFocus) state.trigger.focus({preventScroll: true});
        if (state.panel.matches(':popover-open')) state.panel.hidePopover();
        state.root.open = false;
        state.suppressFocus = false;
        if (active === state) active = null;
    }

    function open(state, reason) {
        if (reason === 'focus' && state.dismissed) return;
        if (reason === 'hover' && active && active !== state && hasFocus(active)) return;
        clearTimeout(state.closeTimer);
        if (active && active !== state) close(active);
        state.dismissed = false;
        state.root.open = true;
        if (!state.panel.matches(':popover-open')) state.panel.showPopover();
        active = state;
        place(state);
    }

    function scheduleClose(state) {
        clearTimeout(state.closeTimer);
        state.closeTimer = setTimeout(() => {
            if (!state.pinned && !state.hovered.size && !hasFocus(state)) close(state);
        }, 240);
    }

    for (const root of document.querySelectorAll('[data-score-explainer]')) {
        const trigger = root.querySelector('summary');
        const panel = root.querySelector('[data-score-panel]');
        if (!trigger || !panel) continue;
        const state = {root, trigger, panel, pinned: false, dismissed: false, suppressFocus: false, hovered: new Set(), closeTimer: 0};
        panel.setAttribute('popover', 'manual');
        root.setAttribute('data-score-enhanced', '');

        for (const surface of [trigger, panel]) {
            surface.addEventListener('pointerenter', event => {
                if (event.pointerType === 'touch') return;
                state.hovered.add(surface);
                clearTimeout(state.closeTimer);
                if (surface === trigger) open(state, 'hover');
            });
            surface.addEventListener('pointerleave', event => {
                if (event.pointerType === 'touch') return;
                state.hovered.delete(surface);
                scheduleClose(state);
            });
        }
        trigger.addEventListener('click', event => {
            event.preventDefault();
            if (state.pinned && root.open) close(state);
            else { state.pinned = true; open(state, 'click'); }
        });
        root.addEventListener('focusin', () => {
            if (!state.suppressFocus && !pointerFocus) open(state, 'focus');
        });
        root.addEventListener('focusout', () => {
            setTimeout(() => {
                if (!hasFocus(state)) {
                    if (!state.hovered.size) close(state);
                    state.dismissed = false;
                }
            }, 0);
        });
        panel.querySelector('[data-score-close]')?.addEventListener('click', () => close(state, true));
        panel.querySelector('[data-score-show-sources]')?.addEventListener('click', event => {
            const sources = document.querySelector('#seller-verification .instagram-method');
            if (sources) {
                event.preventDefault();
                sources.open = true;
                close(state);
                sources.querySelector('summary')?.focus({preventScroll: true});
                history.replaceState(null, '', '#seller-verification');
                sources.scrollIntoView({block: 'start', behavior: 'auto'});
            }
        });
    }

    document.addEventListener('pointerdown', event => {
        if (active && !active.root.contains(event.target)) close(active);
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && active) {
            event.preventDefault();
            close(active, hasFocus(active));
        }
    });
    function queuePlacement() {
        if (frame || !active) return;
        frame = requestAnimationFrame(() => { frame = 0; if (active) place(active); });
    }
    window.addEventListener('resize', queuePlacement, {passive: true});
    window.addEventListener('scroll', queuePlacement, {passive: true, capture: true});
    document.fonts?.ready.then(queuePlacement);
})();
