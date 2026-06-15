// Toast notifications
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `fixed top-4 right-4 z-50 rounded-xl px-4 py-3 text-sm font-medium shadow-lg ring-1 transition-all duration-300 ${
    type === 'success' 
      ? 'bg-emerald-500/10 text-emerald-200 ring-emerald-500/30' 
      : type === 'error'
      ? 'bg-rose-500/10 text-rose-200 ring-rose-500/30'
      : 'bg-sky-500/10 text-sky-200 ring-sky-500/30'
  }`;
  toast.textContent = message;
  toast.style.opacity = '0';
  toast.style.transform = 'translateY(-10px)';
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  }, 10);
  
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Confirmation dialogs
function confirmAction(message, onConfirm) {
  if (confirm(message)) {
    onConfirm();
  }
}
