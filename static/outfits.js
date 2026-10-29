/* Enhance native checkboxes and forms; every save also works without JavaScript. */
(() => {
  'use strict';
  const form = document.querySelector('[data-outfit-editor]');
  if (!form) return;
  const inputs = [...form.querySelectorAll('input[name="item_ids"]')];
  const maximum = Number(form.dataset.maxPieces);
  const count = form.querySelector('[data-outfit-count]');
  const preview = form.querySelector('[data-outfit-preview]');
  const empty = form.querySelector('[data-outfit-preview-empty]');
  const save = form.querySelector('[data-outfit-save]');
  const hint = form.querySelector('[data-outfit-save-hint]');
  function update() {
    const chosen = inputs.filter(input => input.checked);
    count.textContent = `${chosen.length} of ${maximum} selected`;
    preview.replaceChildren();
    for (const input of inputs) {
      input.disabled = !input.checked && chosen.length >= maximum;
    }
    for (const input of chosen) {
      const source = input.closest('.outfit-choice').querySelector('.photo-frame');
      const thumbnail = source.cloneNode(true);
      thumbnail.querySelectorAll('img').forEach(img => { img.loading = 'eager'; });
      preview.append(thumbnail);
    }
    preview.hidden = !chosen.length;
    empty.hidden = !!chosen.length;
    save.disabled = !chosen.length || chosen.length > maximum;
    hint.hidden = !!chosen.length;
    hint.textContent = 'Choose at least one piece to save your outfit.';
  }
  form.addEventListener('change', event => {
    if (event.target.matches('input[name="item_ids"]')) update();
  });
  // Native POST navigation keeps database errors and validation fully visible.
  // The server also deduplicates retried creates and rejects stale edits.
  form.addEventListener('submit', () => {
    save.disabled = true;
    save.setAttribute('aria-busy', 'true');
    save.textContent = 'Saving your outfit...';
  });
  window.addEventListener('pageshow', () => {
    save.removeAttribute('aria-busy');
    save.innerHTML = form.querySelector('[name="version"]') ? 'Save changes <span aria-hidden="true">→</span>' : 'Save outfit <span aria-hidden="true">→</span>';
    update();
  });
  update();
  const errors = document.querySelector('[data-outfit-errors]');
  if (errors) errors.focus();
})();
