/* Amigo do Professor — main.js */

// ── Sidebar toggle ─────────────────────────────────
const sidebar = document.getElementById('sidebar');
const menuToggle = document.getElementById('menuToggle');
const sidebarClose = document.getElementById('sidebarClose');
const overlay = document.getElementById('sidebarOverlay');

function openSidebar() {
  sidebar?.classList.add('open');
  overlay?.classList.add('show');
  document.body.style.overflow = 'hidden';
}
function closeSidebar() {
  sidebar?.classList.remove('open');
  overlay?.classList.remove('show');
  document.body.style.overflow = '';
}

menuToggle?.addEventListener('click', openSidebar);
sidebarClose?.addEventListener('click', closeSidebar);
overlay?.addEventListener('click', closeSidebar);

// Close on nav link click (mobile)
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', () => {
    if (window.innerWidth <= 768) closeSidebar();
  });
});

// ── Flash auto-dismiss ─────────────────────────────
setTimeout(() => {
  document.querySelectorAll('.flash').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(-8px)';
    el.style.transition = 'all .3s ease';
    setTimeout(() => el.remove(), 300);
  });
}, 4000);

// ── Frequency status color ─────────────────────────
document.querySelectorAll('.status-select').forEach(sel => {
  function updateColor() {
    sel.className = 'status-select ' + sel.value;
  }
  updateColor();
  sel.addEventListener('change', updateColor);
});

// ── Biometric (WebAuthn) ───────────────────────────
const bioBtn = document.getElementById('biometricBtn');

async function checkBiometricAvailability() {
  if (!bioBtn) return;
  try {
    const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    if (available) {
      bioBtn.classList.remove('hidden');
    }
  } catch(e) { /* not supported */ }
}
checkBiometricAvailability();

bioBtn?.addEventListener('click', async () => {
  try {
    // Simple credential get for demo — in production integrate with WebAuthn server
    const credential = await navigator.credentials.get({
      publicKey: {
        challenge: crypto.getRandomValues(new Uint8Array(32)),
        timeout: 60000,
        userVerification: 'required',
        rpId: window.location.hostname,
      }
    });
    if (credential) {
      bioBtn.textContent = '✓ Biometria verificada';
      bioBtn.style.borderColor = 'var(--sage-500)';
      bioBtn.style.color = 'var(--sage-600)';
      // In production: send credential to server for verification
    }
  } catch (e) {
    if (e.name !== 'NotAllowedError') {
      alert('Biometria não disponível neste dispositivo.');
    }
  }
});

// ── Date picker: set today as default ─────────────
document.querySelectorAll('input[type="date"]:not([value])').forEach(input => {
  if (!input.value) {
    input.value = new Date().toISOString().slice(0, 10);
  }
});

// ── Confirm delete ─────────────────────────────────
document.querySelectorAll('form[data-confirm]').forEach(form => {
  form.addEventListener('submit', e => {
    if (!confirm(form.dataset.confirm || 'Confirma a exclusão?')) {
      e.preventDefault();
    }
  });
});

// ── Nota input coloring ────────────────────────────
document.querySelectorAll('.nota-input').forEach(input => {
  function colorNote() {
    const v = parseFloat(input.value);
    const max = parseFloat(input.dataset.max || 10);
    input.style.borderColor = isNaN(v) ? '' : v >= max * 0.6 ? 'var(--sage-500)' : 'var(--rose-500)';
  }
  input.addEventListener('input', colorNote);
  colorNote();
});
