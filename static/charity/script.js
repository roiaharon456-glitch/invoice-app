(() => {
  const KEY_TOTAL = 'charityBox:totalAgorot';
  const KEY_DAILY = 'charityBox:dailyAgorot';
  const KEY_DAILY_DATE = 'charityBox:dailyDate';
  const KEY_CHARITY = 'charityBox:charityName';

  const els = {
    dailyAmount: document.getElementById('daily-amount'),
    totalAmount: document.getElementById('total-amount'),
    coins: Array.from(document.querySelectorAll('.coin')),
    emptyBtn: document.getElementById('empty-btn'),
    assignBtn: document.getElementById('assign-btn'),
    charityLine: document.getElementById('charity-line'),
    charityNameDisplay: document.getElementById('charity-name-display'),

    modalOverlay: document.getElementById('modal-overlay'),
    modalClose: document.getElementById('modal-close'),
    panelConfirm: document.getElementById('panel-confirm'),
    panelResult: document.getElementById('panel-result'),
    confirmText: document.getElementById('confirm-text'),
    resultTitle: document.getElementById('result-title'),
    cancelEmptyBtn: document.getElementById('cancel-empty-btn'),
    confirmEmptyBtn: document.getElementById('confirm-empty-btn'),
    doneBtn: document.getElementById('done-btn'),

    charityModalOverlay: document.getElementById('charity-modal-overlay'),
    charityModalClose: document.getElementById('charity-modal-close'),
    charityNameInput: document.getElementById('charity-name-input'),
    charityCancelBtn: document.getElementById('charity-cancel-btn'),
    charitySaveBtn: document.getElementById('charity-save-btn'),
  };

  let storageAvailable = true;
  let totalAgorot = 0;
  let dailyAgorot = 0;
  let charityName = '';

  function todayStr() {
    const d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }

  function safeGet(key) {
    try { return localStorage.getItem(key); } catch (e) { storageAvailable = false; return null; }
  }
  function safeSet(key, value) {
    if (!storageAvailable) return;
    try { localStorage.setItem(key, value); } catch (e) { storageAvailable = false; }
  }

  function loadState() {
    const rawTotal = parseInt(safeGet(KEY_TOTAL), 10);
    totalAgorot = Number.isFinite(rawTotal) && rawTotal >= 0 ? rawTotal : 0;

    const storedDate = safeGet(KEY_DAILY_DATE);
    const rawDaily = parseInt(safeGet(KEY_DAILY), 10);
    const validDaily = Number.isFinite(rawDaily) && rawDaily >= 0 ? rawDaily : 0;
    if (storedDate === todayStr()) {
      dailyAgorot = validDaily;
    } else {
      dailyAgorot = 0;
      safeSet(KEY_DAILY_DATE, todayStr());
      safeSet(KEY_DAILY, '0');
    }

    charityName = safeGet(KEY_CHARITY) || '';
  }

  function rolloverDailyIfNeeded() {
    const today = todayStr();
    if (safeGet(KEY_DAILY_DATE) !== today) {
      dailyAgorot = 0;
      safeSet(KEY_DAILY_DATE, today);
      safeSet(KEY_DAILY, '0');
      renderTotals();
    }
  }

  function formatAgorot(agorot) {
    const shekels = agorot / 100;
    return '₪' + shekels.toLocaleString('he-IL', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function renderTotals() {
    els.dailyAmount.textContent = formatAgorot(dailyAgorot);
    els.totalAmount.textContent = formatAgorot(totalAgorot);
    els.emptyBtn.disabled = totalAgorot === 0;
  }

  function bump(el) {
    el.classList.remove('bump');
    void el.offsetWidth;
    el.classList.add('bump');
  }

  function renderCharity() {
    if (charityName) {
      els.charityNameDisplay.textContent = charityName;
      els.charityLine.hidden = false;
    } else {
      els.charityLine.hidden = true;
    }
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

  function handleCoinTap(coinEl) {
    rolloverDailyIfNeeded();
    const value = parseInt(coinEl.dataset.value, 10);

    dailyAgorot += value;
    totalAgorot += value;
    safeSet(KEY_DAILY, String(dailyAgorot));
    safeSet(KEY_TOTAL, String(totalAgorot));

    renderTotals();
    bump(els.dailyAmount);
    bump(els.totalAmount);
    playDrop(coinEl);
    floatFeedback(coinEl, value);
  }

  function openEmptyModal() {
    els.confirmText.textContent = `בקופה כרגע ${formatAgorot(totalAgorot)}. הפעולה תאפס את הסכום שהצטבר (הסכום היומי לא יושפע).`;
    showPanel(els.panelConfirm);
    els.modalOverlay.hidden = false;
    els.confirmEmptyBtn.focus();
    document.addEventListener('keydown', onEmptyModalKeydown);
  }

  function closeEmptyModal() {
    els.modalOverlay.hidden = true;
    document.removeEventListener('keydown', onEmptyModalKeydown);
    els.emptyBtn.focus();
  }

  function onEmptyModalKeydown(e) { if (e.key === 'Escape') closeEmptyModal(); }

  function showPanel(panel) {
    els.panelConfirm.classList.toggle('active', panel === els.panelConfirm);
    els.panelResult.classList.toggle('active', panel === els.panelResult);
  }

  function performEmpty() {
    const preClear = totalAgorot;
    totalAgorot = 0;
    safeSet(KEY_TOTAL, '0');
    renderTotals();
    els.resultTitle.textContent = `תרמת ${formatAgorot(preClear)}!`;
    showPanel(els.panelResult);
  }

  function openCharityModal() {
    els.charityNameInput.value = charityName;
    els.charityModalOverlay.hidden = false;
    els.charityNameInput.focus();
    document.addEventListener('keydown', onCharityModalKeydown);
  }

  function closeCharityModal() {
    els.charityModalOverlay.hidden = true;
    document.removeEventListener('keydown', onCharityModalKeydown);
    els.assignBtn.focus();
  }

  function onCharityModalKeydown(e) { if (e.key === 'Escape') closeCharityModal(); }

  function saveCharity() {
    charityName = els.charityNameInput.value.trim();
    safeSet(KEY_CHARITY, charityName);
    renderCharity();
    closeCharityModal();
  }

  els.coins.forEach((coinEl) => coinEl.addEventListener('click', () => handleCoinTap(coinEl)));

  els.emptyBtn.addEventListener('click', openEmptyModal);
  els.modalClose.addEventListener('click', closeEmptyModal);
  els.cancelEmptyBtn.addEventListener('click', closeEmptyModal);
  els.confirmEmptyBtn.addEventListener('click', performEmpty);
  els.doneBtn.addEventListener('click', closeEmptyModal);
  els.modalOverlay.addEventListener('click', (e) => { if (e.target === els.modalOverlay) closeEmptyModal(); });

  els.assignBtn.addEventListener('click', openCharityModal);
  els.charityModalClose.addEventListener('click', closeCharityModal);
  els.charityCancelBtn.addEventListener('click', closeCharityModal);
  els.charitySaveBtn.addEventListener('click', saveCharity);
  els.charityNameInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') saveCharity(); });
  els.charityModalOverlay.addEventListener('click', (e) => { if (e.target === els.charityModalOverlay) closeCharityModal(); });

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') rolloverDailyIfNeeded();
  });

  loadState();
  renderTotals();
  renderCharity();
})();
