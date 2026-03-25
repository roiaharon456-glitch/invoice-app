let currentUser = null;
let currentStep = 'name';

/* ── Navigation ── */
function showStep(id) {
  document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
  document.getElementById('step-' + id).classList.add('active');
  currentStep = id;
  hideError();
  updateProgress(id);
}

function updateProgress(id) {
  const map = { name: 1, bank: 2, existing: 2, 'edit-bank': 2, upload: 3, loading: 3, success: 3 };
  const step = map[id] || 1;
  const pct = (step / 3) * 100;
  document.getElementById('progress-fill').style.width = pct + '%';

  document.querySelectorAll('.step-dot').forEach(dot => {
    const n = parseInt(dot.dataset.step);
    dot.classList.remove('active', 'done');
    if (n === step) dot.classList.add('active');
    if (n < step)  dot.classList.add('done');
  });

  document.querySelectorAll('.step-connector').forEach((c, i) => {
    c.classList.toggle('done', i + 1 < step);
  });
}

/* ── Error ── */
function showError(msg) {
  const box = document.getElementById('error-box');
  document.getElementById('error-text').textContent = msg;
  box.style.display = 'flex';
}
function hideError() {
  document.getElementById('error-box').style.display = 'none';
}

/* ── Step 1: check user ── */
async function checkUser() {
  const name = document.getElementById('name').value.trim();
  if (!name) { showError('אנא הכנס שם מלא'); return; }

  try {
    const res = await fetch(`/api/check-user?name=${encodeURIComponent(name)}`);
    const data = await res.json();
    if (data.exists) {
      currentUser = data.user;
      document.getElementById('welcome-name').textContent = `שלום, ${data.user.name}!`;
      renderBankDetails(data.user);
      showStep('existing');
    } else {
      currentUser = { name };
      showStep('bank');
    }
  } catch {
    showError('שגיאת תקשורת, אנא נסה שוב');
  }
}

function renderBankDetails(user) {
  const rows = [
    ['שם בעל החשבון', user.account_holder],
    ['בנק',           `${user.bank_name} (${user.bank_number})`],
    ['סניף',          user.branch_number],
    ['מספר חשבון',   user.account_number],
  ];
  document.getElementById('bank-details-display').innerHTML = rows.map(([label, val]) => `
    <div class="bank-row">
      <span class="bank-row-label">${label}</span>
      <span class="bank-row-value">${val}</span>
    </div>
  `).join('');
}

/* ── Step 2b: edit bank ── */
function showEditBank() {
  ['account_holder','bank_name','bank_number','branch_number','account_number'].forEach(f => {
    document.getElementById('edit_' + f).value = currentUser[f] || '';
  });
  showStep('edit-bank');
}

function cancelEdit() { showStep('existing'); }

async function updateBank() {
  const fields = getFields('edit_', ['account_holder','bank_name','bank_number','branch_number','account_number']);
  if (!fields) return;

  const form = new FormData();
  form.append('name', currentUser.name);
  Object.entries(fields).forEach(([k, v]) => form.append(k, v));

  try {
    const res = await fetch('/api/update-user', { method: 'PUT', body: form });
    if (res.ok) {
      currentUser = { ...currentUser, ...fields };
      renderBankDetails(currentUser);
      showStep('existing');
    } else {
      showError('שגיאה בשמירת הפרטים');
    }
  } catch {
    showError('שגיאת תקשורת, אנא נסה שוב');
  }
}

function getFields(prefix, keys) {
  const result = {};
  for (const k of keys) {
    const v = document.getElementById((prefix || '') + k).value.trim();
    if (!v) { showError('אנא מלא את כל השדות'); return null; }
    result[k] = v;
  }
  return result;
}

/* ── Step 2a → upload ── */
function goToUpload() {
  if (currentStep === 'bank') {
    const fields = getFields('', ['account_holder','bank_name','bank_number','branch_number','account_number']);
    if (!fields) return;
    currentUser = { ...currentUser, ...fields };
  }
  showStep('upload');
}

/* ── Upload ── */
function previewImage(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = e => {
    document.getElementById('preview-img').src = e.target.result;
    document.getElementById('upload-preview').style.display = 'flex';
    document.getElementById('upload-content').style.display = 'none';
    document.getElementById('submit-btn').disabled = false;
    document.getElementById('btn-change').style.display = 'flex';
  };
  reader.readAsDataURL(file);
}

function clearImage() {
  document.getElementById('invoice-input').value = '';
  document.getElementById('upload-preview').style.display = 'none';
  document.getElementById('upload-content').style.display = 'flex';
  document.getElementById('submit-btn').disabled = true;
  document.getElementById('btn-change').style.display = 'none';
}

/* ── Submit ── */
async function submitForm() {
  const fileInput = document.getElementById('invoice-input');
  if (!fileInput.files[0]) { showError('אנא העלה תמונת חשבונית'); return; }

  const form = new FormData();
  form.append('name', currentUser.name);
  form.append('invoice', fileInput.files[0]);

  const isNew = !currentUser.id;
  if (isNew) {
    ['account_holder','bank_name','bank_number','branch_number','account_number'].forEach(f => {
      form.append(f, currentUser[f] || '');
    });
  }

  showStep('loading');
  animateLoadingSteps();

  try {
    const res = await fetch('/api/submit', { method: 'POST', body: form });
    const data = await res.json();

    if (res.ok && data.success) {
      showStep('success');
      document.getElementById('success-details').innerHTML = `
        <div>שם: <strong>${currentUser.name}</strong></div>
        <div>חשבון: <strong>${currentUser.bank_number} / ${currentUser.branch_number} / ${currentUser.account_number}</strong></div>
      `;
    } else {
      showStep('upload');
      showError(data.detail || 'שגיאה בשליחת הבקשה');
    }
  } catch {
    showStep('upload');
    showError('שגיאת תקשורת, אנא נסה שוב');
  }
}

function animateLoadingSteps() {
  const steps = ['load-1', 'load-2', 'load-3'];
  steps.forEach(id => {
    const el = document.getElementById(id);
    el.classList.remove('active', 'done');
  });
  document.getElementById('load-1').classList.add('active');

  setTimeout(() => {
    document.getElementById('load-1').classList.replace('active', 'done');
    document.getElementById('load-2').classList.add('active');
  }, 2000);

  setTimeout(() => {
    document.getElementById('load-2').classList.replace('active', 'done');
    document.getElementById('load-3').classList.add('active');
  }, 4000);
}

/* ── Reset ── */
function resetForm() {
  currentUser = null;
  document.getElementById('name').value = '';
  clearImage();
  showStep('name');
}

/* ── Enter key ── */
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && currentStep === 'name') checkUser();
});
