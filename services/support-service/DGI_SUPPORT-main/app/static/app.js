const __uiInit = () => {
  try {
    window.__uiReady = true;
  const root = document.documentElement;
  const btn = document.getElementById('themeToggle');
  const openSettings = document.getElementById('openSettings');
  const settingsModal = document.getElementById('settingsModal');
  const userMenuBtn = document.getElementById('userMenuBtn');
  const userMenuPanel = document.getElementById('userMenuPanel');

  const applyThemeFlag = () => {
    const p = root.dataset.preset || 'dark';
    root.dataset.theme = (p === 'light' || p === 'sand' || p === 'paper') ? 'light' : 'dark';
    if (btn) {
      const t = root.dataset.theme || 'dark';
      btn.textContent = t === 'light' ? '☾' : '☀';
    }
  };

  const get = (k, fallback) => {
    try {
      return localStorage.getItem(k) || fallback;
    } catch (e) {
      return fallback;
    }
  };
  const set = (k, v) => {
    try {
      localStorage.setItem(k, v);
    } catch (e) {}
  };

  const rgbToHex = (rgb) => {
    const s = (rgb || '').trim();
    if (!s) return '';
    if (s.startsWith('#')) return s;

    const m = s.match(/rgba?\((\d+)[,\s]+(\d+)[,\s]+(\d+)/i);
    if (m) {
      const r = Number(m[1]);
      const g = Number(m[2]);
      const b = Number(m[3]);
      const to2 = (n) => n.toString(16).padStart(2, '0');
      return `#${to2(r)}${to2(g)}${to2(b)}`;
    }

    const m2 = s.match(/rgb\((\d+)\s+(\d+)\s+(\d+)\)/i);
    if (m2) {
      const r = Number(m2[1]);
      const g = Number(m2[2]);
      const b = Number(m2[3]);
      const to2 = (n) => n.toString(16).padStart(2, '0');
      return `#${to2(r)}${to2(g)}${to2(b)}`;
    }

    return '';
  };

  const wireColor = (id, key, cssVar) => {
    const el = document.getElementById(id);
    if (!el) return;

    const stored = get(key, '');
    if (stored) {
      root.style.setProperty(cssVar, stored);
      if (el instanceof HTMLInputElement) el.value = stored;
    } else {
      const cur = getComputedStyle(root).getPropertyValue(cssVar);
      const hex = rgbToHex(cur);
      if (hex && el instanceof HTMLInputElement) el.value = hex;
    }

    el.addEventListener('input', () => {
      if (!(el instanceof HTMLInputElement)) return;
      root.style.setProperty(cssVar, el.value);
      set(key, el.value);
    });
  };

  const setMenuOpen = (open) => {
    if (!userMenuBtn || !userMenuPanel) return;
    userMenuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    userMenuPanel.classList.toggle('hidden', !open);
    userMenuPanel.setAttribute('aria-hidden', open ? 'false' : 'true');
  };

  if (userMenuBtn && userMenuPanel) {
    userMenuBtn.addEventListener('click', () => {
      try { console.log('userMenuBtn click'); } catch (e) {}
      const open = userMenuPanel.classList.contains('hidden');
      setMenuOpen(open);
    });

    document.addEventListener('click', (e) => {
      const target = e.target;
      if (!(target instanceof Node)) return;
      if (userMenuBtn.contains(target) || userMenuPanel.contains(target)) return;
      setMenuOpen(false);
    });

    userMenuPanel.addEventListener('click', (e) => {
      const target = e.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.closest('a') || target.closest('button')) setMenuOpen(false);
    });
  }

  root.dataset.preset = root.dataset.preset || get('ui.preset', root.dataset.preset || 'dark');
  root.dataset.accent = 'dgi';
  root.dataset.density = root.dataset.density || get('ui.density', root.dataset.density || 'cozy');
  root.dataset.font = root.dataset.font || get('ui.font', root.dataset.font || 'md');
  root.dataset.glow = 'med';
  root.dataset.motion = root.dataset.motion || get('ui.motion', root.dataset.motion || 'normal');
  document.documentElement.setAttribute('lang', 'ru');
  applyThemeFlag();

  const presetSel = document.getElementById('uiPreset');
  const densitySel = document.getElementById('uiDensity');
  const fontSel = document.getElementById('uiFont');
  const resetBtn = document.getElementById('uiReset');
  const motionSel = document.getElementById('uiMotion');

  if (presetSel) presetSel.value = root.dataset.preset || 'dark';
  if (densitySel) densitySel.value = root.dataset.density || 'cozy';
  if (fontSel) fontSel.value = root.dataset.font || 'md';
  if (motionSel) motionSel.value = root.dataset.motion || 'normal';

  const wire = (el, key, attr, after) => {
    if (!el) return;
    el.addEventListener('change', () => {
      root.dataset[attr] = el.value;
      set(key, el.value);
      if (after) after();
    });
  };

  wire(presetSel, 'ui.preset', 'preset', applyThemeFlag);
  wire(densitySel, 'ui.density', 'density');
  wire(fontSel, 'ui.font', 'font');
  wire(motionSel, 'ui.motion', 'motion');

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      try {
        localStorage.removeItem('ui.preset');
        localStorage.removeItem('ui.density');
        localStorage.removeItem('ui.font');
        localStorage.removeItem('ui.motion');
      } catch (e) {}
      window.location.reload();
    });
  }

  if (btn) {
    btn.addEventListener('click', () => {
      const t = root.dataset.theme || 'dark';
      const next = t === 'light' ? 'dark' : 'light';
      root.dataset.preset = next === 'light' ? 'light' : 'dark';
      set('ui.preset', root.dataset.preset);
      if (presetSel) presetSel.value = root.dataset.preset;
      applyThemeFlag();
      setActiveSwatches();
    });
  }

  const setTab = (name) => {
    for (const p of tabPanels) {
      const el = p;
      el.classList.toggle('hidden', el.getAttribute('data-panel') !== name);
    }
  };

  if (tabBtns.length) {
    setTab('theme');
    for (const b of tabBtns) {
      b.addEventListener('click', () => {
        const name = b.getAttribute('data-tab');
        if (name) setTab(name);
      });
    }
  }

  const setModalOpen = (open) => {
    if (!settingsModal) return;
    settingsModal.classList.toggle('hidden', !open);
    settingsModal.setAttribute('aria-hidden', open ? 'false' : 'true');
  };

  if (openSettings) {
    openSettings.addEventListener('click', () => setModalOpen(true));
  }

  if (settingsModal) {
    settingsModal.addEventListener('click', (e) => {
      const target = e.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.getAttribute('data-close') === 'true') {
        setModalOpen(false);
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      setModalOpen(false);
      setMenuOpen(false);
    }
  });

  const needsConfirm = (form, submitter) => {
    const action = (form && form.getAttribute && form.getAttribute('action')) || '';
    const submitAction = (submitter && submitter.getAttribute && submitter.getAttribute('formaction')) || '';
    const cls = (submitter && submitter.classList) ? submitter.classList : null;
    const text = (submitter && submitter.textContent ? submitter.textContent : '').trim().toLowerCase();

    const a = (submitAction || action || '').toLowerCase();
    if (a.includes('/delete')) return true;
    if (a.includes('/logout')) return true;
    if (cls && cls.contains('btn-danger')) return true;
    if (text === 'удалить' || text === 'выйти') return true;
    return false;
  };

  const confirmMessage = (form, submitter) => {
    const action = ((submitter && submitter.getAttribute && submitter.getAttribute('formaction')) || (form && form.getAttribute && form.getAttribute('action')) || '').toLowerCase();
    if (action.includes('/logout')) return 'Выйти из аккаунта?';
    return 'Удалить? Это действие нельзя отменить.';
  };

  document.addEventListener('submit', (e) => {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;
    const submitter = e.submitter instanceof HTMLElement ? e.submitter : null;
    if (!needsConfirm(form, submitter)) return;
    if (!window.confirm(confirmMessage(form, submitter))) {
      e.preventDefault();
      e.stopPropagation();
    }
  }, true);

  document.addEventListener('click', (e) => {
    const target = e.target;
    if (!(target instanceof HTMLElement)) return;
    const btn = target.closest('button[formaction]');
    if (!btn) return;
    const fa = (btn.getAttribute('formaction') || '').toLowerCase();
    if (!fa.includes('/delete')) return;
    if (!window.confirm('Удалить? Это действие нельзя отменить.')) {
      e.preventDefault();
      e.stopPropagation();
    }
  }, true);

  const appFilters = document.querySelectorAll('form[action="/app"][method="get"]');
  for (const f of appFilters) {
    const qInput = f.querySelector('input[name="q"]');
    const selects = f.querySelectorAll('select');
    let timer = null;

    const applyBtn = f.querySelector('button[type="submit"]');
    const saveBtn = f.querySelector('[data-save-filter="true"]');
    const savedSel = f.querySelector('[data-saved-filters="true"]');

    const filtersKey = 'app.savedFilters.v1';
    const loadFilters = () => {
      try {
        const raw = localStorage.getItem(filtersKey) || '[]';
        const arr = JSON.parse(raw);
        return Array.isArray(arr) ? arr : [];
      } catch (e) {
        return [];
      }
    };
    const saveFilters = (arr) => {
      try { localStorage.setItem(filtersKey, JSON.stringify(arr)); } catch (e) {}
    };

    const currentParams = () => {
      const fd = new FormData(f);
      const p = new URLSearchParams();
      for (const [k, v] of fd.entries()) {
        if (typeof v !== 'string') continue;
        p.set(k, v);
      }
      return p;
    };
    const snapshot = () => currentParams().toString();
    let initialSnap = snapshot();

    const setApplyEnabled = () => {
      if (!applyBtn) return;
      applyBtn.disabled = snapshot() === initialSnap;
      applyBtn.classList.toggle('opacity-50', applyBtn.disabled);
      applyBtn.classList.toggle('pointer-events-none', applyBtn.disabled);
    };

    const renderSaved = () => {
      if (!savedSel) return;
      const items = loadFilters();
      const cur = savedSel.value;
      savedSel.innerHTML = '<option value="">Мои фильтры…</option>';
      for (const it of items) {
        const opt = document.createElement('option');
        opt.value = it.qs;
        opt.textContent = it.name;
        savedSel.appendChild(opt);
      }
      savedSel.value = cur;
    };

    renderSaved();
    setApplyEnabled();

    if (qInput) {
      qInput.addEventListener('input', () => {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => {}, 0);
        setApplyEnabled();
      });
    }

    for (const s of selects) {
      s.addEventListener('change', () => f.submit());
    }

    for (const s of selects) {
      s.addEventListener('change', () => setApplyEnabled());
    }

    if (saveBtn) {
      saveBtn.addEventListener('click', () => {
        const name = window.prompt('Название фильтра:');
        const n = (name || '').trim();
        if (!n) return;
        const qs = currentParams().toString();
        const items = loadFilters();
        const next = [{ name: n, qs }, ...items.filter((x) => x && x.qs !== qs)].slice(0, 20);
        saveFilters(next);
        renderSaved();
      });
    }

    if (savedSel) {
      savedSel.addEventListener('change', () => {
        const qs = (savedSel.value || '').trim();
        if (!qs) return;
        const url = `/app?${qs}`;
        window.location.href = url;
      });
    }

    f.addEventListener('submit', () => {
      try { initialSnap = snapshot(); } catch (e) {}
      setApplyEnabled();
    });
  }

  const glowCards = document.querySelectorAll('.card-glow');
  for (const card of glowCards) {
    card.addEventListener('mouseenter', () => {
      card.style.setProperty('--mx', '50%');
      card.style.setProperty('--my', '50%');
    });
    card.addEventListener('mousemove', (e) => {
      const r = card.getBoundingClientRect();
      const mx = ((e.clientX - r.left) / r.width) * 100;
      const my = ((e.clientY - r.top) / r.height) * 100;
      card.style.setProperty('--mx', `${mx}%`);
      card.style.setProperty('--my', `${my}%`);
    });
  }

  if (window.location.pathname === '/app') {
    const refresh = root.dataset.refresh || 'off';
    const ms = refresh === '10s' ? 10000 : (refresh === '30s' ? 30000 : (refresh === '60s' ? 60000 : 0));
    if (ms) {
      setInterval(() => {
        if (document.getElementById('settingsModal') && !document.getElementById('settingsModal').classList.contains('hidden')) return;
        const active = document.activeElement;
        if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.tagName === 'SELECT')) return;
        const list = document.getElementById('ticketList');
        if (list && window.htmx) {
          window.htmx.trigger(list, 'refreshTickets');
          return;
        }
        window.location.reload();
      }, ms);
    }
  }
  } catch (err) {
    try { console.error('UI init failed:', err); } catch (e) {}
  }
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', __uiInit);
} else {
  __uiInit();
}
