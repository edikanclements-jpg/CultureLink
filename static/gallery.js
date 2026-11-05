/* Scrollable clothing previews and two views of the original garment photo. */
(() => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    for (const preview of document.querySelectorAll('[data-clothing-preview]')) {
        const track = preview.querySelector('[data-preview-track]');
        const controls = preview.querySelector('[data-preview-controls]');
        const previous = preview.querySelector('[data-preview-prev]');
        const next = preview.querySelector('[data-preview-next]');
        const position = preview.querySelector('[data-preview-position]');
        const pieces = [...track.children];
        let frame = 0;

        function visiblePieces() {
            const left = track.scrollLeft;
            const right = left + track.clientWidth;
            return pieces.map((piece, index) => {
                const start = piece.offsetLeft;
                const end = start + piece.offsetWidth;
                return Math.min(end, right) - Math.max(start, left) >= piece.offsetWidth * .55 ? index : -1;
            }).filter(index => index >= 0);
        }

        function update() {
            const visible = visiblePieces();
            const first = (visible[0] ?? 0) + 1;
            const last = (visible.at(-1) ?? 0) + 1;
            const label = (first === last ? first : first + '–' + last) + ' / ' + pieces.length;
            if (position.textContent !== label) position.textContent = label;
            previous.disabled = track.scrollLeft <= 2;
            next.disabled = track.scrollWidth - track.clientWidth - track.scrollLeft <= 2;
            controls.hidden = previous.disabled && next.disabled;
        }

        function move(direction) {
            const first = visiblePieces()[0] ?? 0;
            const target = pieces[Math.min(pieces.length - 1, Math.max(0, first + direction))];
            if (target) track.scrollTo({left: target.offsetLeft, behavior: reducedMotion.matches ? 'auto' : 'smooth'});
        }

        track.addEventListener('scroll', () => {
            if (!frame) frame = requestAnimationFrame(() => { frame = 0; update(); });
        }, {passive:true});
        previous.addEventListener('click', () => move(-1));
        next.addEventListener('click', () => move(1));
        if (window.ResizeObserver) new ResizeObserver(update).observe(track);
        else window.addEventListener('resize', update, {passive:true});
        update();
    }

    for (const viewer of document.querySelectorAll('[data-photo-viewer]')) {
        const stage = viewer.querySelector('[data-photo-stage]');
        const image = stage.querySelector('img');
        if (!image) continue;
        const photoLink = stage.querySelector('a');
        const controls = viewer.querySelector('[data-photo-controls]');
        const zoomTools = viewer.querySelector('[data-zoom-controls]');
        const still = viewer.querySelector('[data-photo-still]');
        const detail = viewer.querySelector('[data-photo-detail]');
        const zoomIn = viewer.querySelector('[data-zoom-in]');
        const zoomOut = viewer.querySelector('[data-zoom-out]');
        const zoomLevel = viewer.querySelector('[data-zoom-level]');
        const minZoom = 1.25;
        const maxZoom = 3.5;
        let zoomed = false;
        let scale = 2;
        let x = 0;
        let y = 0;
        let drag = null;
        image.draggable = false;

        function update() {
            if (!zoomed || !image.naturalWidth) {
                image.style.removeProperty('transform');
                return;
            }
            // Use the actual contained photo size to bound dragging in each direction.
            const fit = Math.min(image.clientWidth / image.naturalWidth, image.clientHeight / image.naturalHeight);
            const limitX = Math.max(0, (image.naturalWidth * fit * scale - stage.clientWidth) / 2);
            const limitY = Math.max(0, (image.naturalHeight * fit * scale - stage.clientHeight) / 2);
            x = Math.max(-limitX, Math.min(limitX, x));
            y = Math.max(-limitY, Math.min(limitY, y));
            image.style.transform = 'translate(' + x + 'px, ' + y + 'px) scale(' + scale + ')';
            zoomLevel.value = scale + '×';
            zoomOut.disabled = scale <= minZoom;
            zoomIn.disabled = scale >= maxZoom;
        }

        function stopDrag(event) {
            if (drag && (!event || drag.pointerId === event.pointerId)) {
                const pointerId = drag.pointerId;
                drag = null;
                stage.classList.remove('is-dragging');
                if (stage.hasPointerCapture(pointerId)) stage.releasePointerCapture(pointerId);
            }
        }

        function setView(zoom, focus = false) {
            stopDrag();
            zoomed = zoom;
            scale = 2;
            x = y = 0;
            still.setAttribute('aria-pressed', String(!zoom));
            detail.setAttribute('aria-pressed', String(zoom));
            stage.classList.toggle('is-zoomed', zoom);
            zoomTools.hidden = !zoom;
            if (zoom) {
                stage.tabIndex = 0;
                stage.setAttribute('role', 'group');
                stage.setAttribute('aria-label', 'Zoomed photo. Arrow keys pan. Plus and minus change magnification.');
            } else {
                stage.removeAttribute('tabindex');
                stage.removeAttribute('role');
                stage.removeAttribute('aria-label');
            }
            if (photoLink) {
                if (zoom) photoLink.tabIndex = -1;
                else photoLink.removeAttribute('tabindex');
            }
            update();
            if (focus) (zoom ? stage : still).focus({preventScroll:true});
        }

        function magnify(amount) {
            scale = Math.max(minZoom, Math.min(maxZoom, scale + amount));
            update();
        }

        stage.addEventListener('pointerdown', event => {
            if (!zoomed || !event.isPrimary || event.button !== 0) return;
            drag = {pointerId:event.pointerId, clientX:event.clientX, clientY:event.clientY, x, y};
            stage.setPointerCapture(event.pointerId);
            stage.classList.add('is-dragging');
        });
        stage.addEventListener('pointermove', event => {
            if (!drag || drag.pointerId !== event.pointerId) return;
            x = drag.x + event.clientX - drag.clientX;
            y = drag.y + event.clientY - drag.clientY;
            update();
        });
        for (const event of ['pointerup', 'pointercancel', 'lostpointercapture']) stage.addEventListener(event, stopDrag);
        stage.addEventListener('keydown', event => {
            if (!zoomed) return;
            switch (event.key) {
                case 'ArrowUp': y += 32; break;
                case 'ArrowDown': y -= 32; break;
                case 'ArrowLeft': x += 32; break;
                case 'ArrowRight': x -= 32; break;
                case '+': case '=': magnify(.25); break;
                case '-': magnify(-.25); break;
                case 'Escape': setView(false, true); break;
                default: return;
            }
            event.preventDefault();
            update();
        });
        still.addEventListener('click', () => setView(false));
        detail.addEventListener('click', () => { if (!zoomed) setView(true, true); });
        zoomIn.addEventListener('click', () => magnify(.25));
        zoomOut.addEventListener('click', () => magnify(-.25));
        viewer.querySelector('[data-zoom-reset]').addEventListener('click', () => setView(true));
        image.addEventListener('load', () => { controls.hidden = false; update(); });
        image.addEventListener('error', () => { setView(false); controls.hidden = true; });
        if (image.complete && image.naturalWidth) controls.hidden = false;
        if (window.ResizeObserver) new ResizeObserver(update).observe(stage);
        else window.addEventListener('resize', update, {passive:true});
    }
})();
