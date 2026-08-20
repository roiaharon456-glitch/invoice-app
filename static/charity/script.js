(() => {
  const STORAGE_KEY = 'charityBox:totalAgorot';

  const els = {
    totalAmount: document.getElementById('total-amount'),
    modeSingle: document.getElementById('mode-single'),
    modeDouble: document.getElementById('mode-double'),
    hintText: document.getElementById('hint-text'),
    coinRow: document.getElementById('coin-row'),
    coins: Array.from(document.querySelectorAll('.coin')),
    emptyBtn: document.getElementById('empty-btn'),
    modalOverlay: document.getElementById('modal-overlay'),
    modalClose: document.getElementById('modal-close'),
    panelConfirm: document.getElementById('panel-confirm'),
    panelResult: document.getElementById('panel-result'),
    confirmText: document.getElementById('confirm-text'),
    resultTitle: document.getElementById('result-title'),
    cancelEmptyBtn: document.getElementById('cancel-empty-btn'),
    confirmEmptyBtn: document.getElementById('confirm-empty-btn'),
    doneBtn: document.getElementById('done-btn'),
  };

  let storageAvailable = true;
  let mode = 'single';
  let firstSelection = null; // coin <button> element
  let totalAgorot = loadTotal();

  function loadTotal() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const n = parseInt(raw, 10);
      return Number.isFinite(n) && n >= 0 ? n : 0;
    } catch (e) {
      storageAvailable = false;
      return 0;
    }
  }

  function saveTotal() {
    if (!storageAvailable) return;
    try {
      localStorage.setItem(STORAGE_KEY, String(totalAgorot));
    } catch (e) {
      storageAvailable = false;
    }
  }

  function formatAgorot(agorot) {
    const shekels = agorot / 100;
    return '₪' + shekels.toLocaleString('he-IL', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function renderTotal() {
    els.totalAmount.textContent = formatAgorot(totalAgorot);
    els.emptyBtn.disabled = totalAgorot === 0;
  }

  function bumpTotal() {
    els.totalAmount.classList.remove('bump');
    void els.totalAmount.offsetWidth;
    els.totalAmount.classList.add('bump');
  }

  function renderHint() {
    if (mode !== 'double') {
      els.hintText.textContent = '';
      return;
    }
    els.hintText.textContent = firstSelection ? 'בחר מטבע שני' : 'בחר מטבע ראשון';
  }

  function clearSelection() {
    if (firstSelection) {
      firstSelection.classList.remove('selected');
      firstSelection = null;
    }
    renderHint();
  }

  function setMode(newMode) {
    mode = newMode;
    els.modeSingle.classList.toggle('active', mode === 'single');
    els.modeDouble.classList.toggle('active', mode === 'double');
    clearSelection();
  }

  function playDrop(coinEl) {
    coinEl.classList.remove('drop');
    void coinEl.offsetWidth;
    coinEl.classList.add('drop');
  }

  function floatFeedback(coinEl, agorot) {
    const label = document.createElement('span');
    label.className = 'coin-float';
    label.textContent = '+' + formatAgorot(agorot);
    coinEl.appendChild(label);
    label.addEventListener('animationend', () => label.remove());
  }

  function deposit(agorotList, coinEls) {
    const sum = agorotList.reduce((a, b) => a + b, 0);
    totalAgorot += sum;
    saveTotal();
    renderTotal();
    bumpTotal();
    coinEls.forEach((coinEl, i) => {
      playDrop(coinEl);
      floatFeedback(coinEl, agorotList[i]);
    });
  }

  function handleCoinTap(coinEl) {
    const value = parseInt(coinEl.dataset.value, 10);

    if (mode === 'single') {
      deposit([value], [coinEl]);
      return;
    }

    // double mode
    if (!firstSelection) {
      firstSelection = coinEl;
      coinEl.classList.add('selected');
      renderHint();
      return;
    }

    if (firstSelection === coinEl) {
      clearSelection();
      return;
    }

    const firstValue = parseInt(firstSelection.dataset.value, 10);
    const firstEl = firstSelection;
    firstSelection.classList.remove('selected');
    firstSelection = null;
    deposit([firstValue, value], [firstEl, coinEl]);
    renderHint();
  }

  function openModal() {
    els.confirmText.textContent = `בקופה כרגע ${formatAgorot(totalAgorot)}. הפעולה תאפס את הסכום לחלוטין.`;
    showPanel(els.panelConfirm);
    els.modalOverlay.hidden = false;
    els.confirmEmptyBtn.focus();
    document.addEventListener('keydown', onModalKeydown);
  }

  function closeModal() {
    els.modalOverlay.hidden = true;
    document.removeEventListener('keydown', onModalKeydown);
    els.emptyBtn.focus();
  }

  function onModalKeydown(e) {
    if (e.key === 'Escape') closeModal();
  }

  function showPanel(panel) {
    els.panelConfirm.classList.toggle('active', panel === els.panelConfirm);
    els.panelResult.classList.toggle('active', panel === els.panelResult);
  }

  function performEmpty() {
    const preClear = totalAgorot;
    clearSelection();
    totalAgorot = 0;
    saveTotal();
    renderTotal();
    els.resultTitle.textContent = `תרמת ${formatAgorot(preClear)}!`;
    showPanel(els.panelResult);
  }

  els.modeSingle.addEventListener('click', () => setMode('single'));
  els.modeDouble.addEventListener('click', () => setMode('double'));

  els.coins.forEach((coinEl) => {
    coinEl.addEventListener('click', () => handleCoinTap(coinEl));
  });

  els.emptyBtn.addEventListener('click', openModal);
  els.modalClose.addEventListener('click', closeModal);
  els.cancelEmptyBtn.addEventListener('click', closeModal);
  els.confirmEmptyBtn.addEventListener('click', performEmpty);
  els.doneBtn.addEventListener('click', closeModal);
  els.modalOverlay.addEventListener('click', (e) => {
    if (e.target === els.modalOverlay) closeModal();
  });

  renderTotal();
  renderHint();
})();
