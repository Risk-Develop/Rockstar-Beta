(function () {
  'use strict';

  const configSection = document.getElementById('exit-interview-config');
  const searchInput   = document.getElementById('search-input');
  const statusSelect  = document.getElementById('status-filter');
  const resultsRoot   = document.getElementById('exit-interview-results');
  const hiddenSlug    = 'selected-';

  const CFG = configSection
    ? {
        notificationsUrl:   configSection.dataset.notificationsUrl   || '',
        bulkStatusUrl:      configSection.dataset.bulkStatusUrl      || '',
        bulkMarkReadUrl:    configSection.dataset.bulkMarkReadUrl    || '',
        notifBasePath:      configSection.dataset.notifBasePath      || '',
        csrfToken:          configSection.dataset.csrfToken           || '',
      }
    : {
        notificationsUrl: '', bulkStatusUrl: '', bulkMarkReadUrl: '',
        notifBasePath: '', csrfToken: '',
      };

  window.exitInterviewUI = {
    viewMode: 'list',
    pageSize: 20,
    visibleColumns: {},
    presets: null,
    notificationCount: 0,
    toast(message, type) {
      if (typeof window.showToast === 'function') {
        window.showToast(message, type);
      }
    },
  };

  function getSelectedStatusKey() {
    return hiddenSlug + 'status';
  }

  function loadSelectedStatus() {
    try {
      return localStorage.getItem(getSelectedStatusKey()) || '';
    } catch {
      return '';
    }
  }

  function saveSelectedStatus(val) {
    try {
      localStorage.setItem(getSelectedStatusKey(), val || '');
    } catch {}
  }

  function applyStatusFilter(status) {
    if (!resultsRoot) return;
    var rows = resultsRoot.querySelectorAll('tbody tr[data-status]');
    rows.forEach(function (row) {
      if (!status || row.getAttribute('data-status') === status) {
        row.style.display = '';
      } else {
        row.style.display = 'none';
      }
    });
  }

  function getCurrentViewState() {
    return {
      status: statusSelect ? statusSelect.value : '',
    };
  }

  function saveViewState(state) {
    try {
      localStorage.setItem('xselected-interview-view-state', JSON.stringify(state || {}));
    } catch {}
  }

  function invalidateView() {
    saveViewState(getCurrentViewState());
  }

  // ── Reusable source element (buttons, selects, events call this) ─────────────
  function buildHiddenForm(actionUrl, extraParams) {
    var form = document.createElement('form');
    form.method = 'POST';
    form.action  = actionUrl;
    form.style.display = 'none';

    var csrfEl = document.createElement('input');
    csrfEl.type  = 'hidden';
    csrfEl.name  = 'csrfmiddlewaretoken';
    csrfEl.value = CFG.csrfToken;
    form.appendChild(csrfEl);

    Object.keys(extraParams || {}).forEach(function (name) {
      if (name === 'csrfmiddlewaretoken') return;
      var el = document.createElement('input');
      el.type        = 'hidden';
      el.name        = name;
      el.value       = extraParams[name];
      form.appendChild(el);
    });

    document.body.appendChild(form);
    return form;
  }

  // ── Exported button helpers ──────────────────────────────────────────────────

  function buildStructureSource(ev) {
    if (ev && ev.currentTarget) {
      return ev.currentTarget;
    }
    return document;
  }

  // ── Modal helpers ────────────────────────────────────────────────────────────
  function showQuickViewModal() {
    var el = document.getElementById('quickViewModal');
    if (el) el.style.display = 'flex';
  }

  function closeQuickViewModal() {
    var el = document.getElementById('quickViewModal');
    if (el) el.style.display = 'none';
    var c = document.getElementById('quickViewContent');
    if (c) c.innerHTML = '';
  }

  // ── Bulk actions ─────────────────────────────────────────────────────────────
  function collectSelectedIds() {
    return [...document.querySelectorAll('.row-checkbox:checked')]
      .map(function (cb) { return cb.dataset.pk; });
  }

  function onRowCheckChanged() {
    var count   = collectSelectedIds().length;
    var toolbar = document.getElementById('bulkToolbar');
    var label   = document.getElementById('bulkToolbarLabel');
    if (label) label.textContent = count + (count === 1 ? ' selected' : ' selected');
    if (toolbar) toolbar.classList.toggle('visible', count > 0);
    syncSelectAllHeader();
  }

  function toggleSelectAll(masterCb) {
    document.querySelectorAll('.row-checkbox').forEach(function (cb) {
      cb.checked = masterCb.checked;
    });
    onRowCheckChanged();
  }

  function syncSelectAllHeader() {
    var master = document.getElementById('selectAll');
    if (!master) return;
    var total   = document.querySelectorAll('.row-checkbox').length;
    var checked = document.querySelectorAll('.row-checkbox:checked').length;
    master.checked       = total > 0 && checked === total;
    master.indeterminate = checked > 0 && checked < total;
  }

  function clearBulkSelection() {
    document.querySelectorAll('.row-checkbox').forEach(function (cb) { cb.checked = false; });
    onRowCheckChanged();
  }

  function applyBulkAction() {
    var ids   = collectSelectedIds();
    var parts = document.getElementById('bulkFieldSelect').value.split('|');
    if (parts.length < 2 || !ids.length) return;
    var field = parts[0], value = parts[1];
    var form  = buildHiddenForm(CFG.bulkStatusUrl, { ids: ids.join(','), field: field, value: value });
    htmx.ajax('POST', form.action, { source: form, target: '#exit-interview-results', swap: 'innerHTML' });
    document.body.removeChild(form);
  }

  function bulkMarkAllAsCompleted() {
    var ids = collectSelectedIds();
    var form = buildHiddenForm(CFG.bulkMarkReadUrl, { ids: ids.join(',') });
    htmx.ajax('POST', form.action, { source: form, target: '#exit-interview-results', swap: 'innerHTML' });
    document.body.removeChild(form);
  }

  // ── View & page-size ─────────────────────────────────────────────────────────
  function setViewMode(mode) {
    window.exitInterviewUI.viewMode = mode;
    var url = new URL(window.location.href);
    url.searchParams.set('view', mode);
    window.location.href = url.toString();
  }

  function setPageSize(size) {
    window.exitInterviewUI.pageSize = size;
    var url = new URL(window.location.href);
    url.searchParams.set('page_size', size);
    window.location.href = url.toString();
  }

  // ── Copy-to-clipboard ────────────────────────────────────────────────────────
  function copyEmployeeId(text) {
    navigator.clipboard.writeText(text).then(function () {
      window.exitInterviewUI.toast('Copied!', 'success');
    }).catch(function () {
      window.exitInterviewUI.toast('Copy failed', 'error');
    });
  }

  function dismissNotification(notifId) {
    if (!notifId || !CFG.csrfToken) return;
    var base = CFG.notifBasePath || '';
    var url  = base.replace(/\/\d+\/read\/?$/, '/' + encodeURIComponent(notifId) + '/read/');
    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': CFG.csrfToken },
    }).then(function () {
      window.exitInterviewUI.notificationCount = Math.max(0, window.exitInterviewUI.notificationCount - 1);
    }).catch(function () {});
  }

  // ── Keyboard ────────────────────────────────────────────────────────────────
  function initKeyboardShortcuts() {
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeQuickViewModal();
    });
  }

  // ── Notifications poll ──────────────────────────────────────────────────────
  function initNotificationPoll() {
    var NOTIF_URL = CFG.notificationsUrl;
    if (!NOTIF_URL) return;

    var poll = function () {
      fetch(NOTIF_URL, { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          window.exitInterviewUI.notificationCount = d.count || 0;
          var badge = document.getElementById('notif-badge');
          if (badge) {
            badge.style.display = (d.count || 0) > 0 ? 'inline-flex' : 'none';
            badge.textContent   = d.count || 0;
          }
        })
        .catch(function () { /* stale session / silent skip */ });
    };
    poll();
    setInterval(poll, 60000);
  }

  // ── Init ────────────────────────────────────────────────────────────────────

  // 1. Seed the select and filter from the URL so a direct link with ?status=exit
  //    is reflected immediately in the dropdown (the native change event fires
  //    automatically and updates localStorage / view-state).
  if (typeof URLSearchParams !== 'undefined') {
    var urlStatus = new URLSearchParams(window.location.search).get('status') || '';
    if (urlStatus !== (statusSelect ? statusSelect.value : '')) {
      if (statusSelect) { statusSelect.value = urlStatus; }
    }
  }

  // 2. Apply saved status from localStorage (or initialized URL value).
  var initialStatus = statusSelect ? statusSelect.value : '';
  applyStatusFilter(initialStatus);
  saveSelectedStatus(initialStatus);

  // 3. Listen for manual changes — persist + re-filter + save view-state.
  if (statusSelect) {
    statusSelect.addEventListener('change', function () {
      saveSelectedStatus(statusSelect.value);
      applyStatusFilter(statusSelect.value);
      invalidateView();
    });
  }

  initKeyboardShortcuts();
  initNotificationPoll();

  // Re-apply status filter after every htmx DOM swap (search/sort/pagination/bulk-action)
  if (typeof htmx !== 'undefined') {
    htmx.on('htmx:afterSwap', function () { applyStatusFilter(statusSelect ? statusSelect.value : ''); });
  }

  // ── Exports for inline onclick / hx-on attributes ────────────────────────────
  window.showQuickViewModal     = showQuickViewModal;
  window.closeQuickViewModal    = closeQuickViewModal;
  window.collectSelectedIds     = collectSelectedIds;
  window.onRowCheckChanged      = onRowCheckChanged;
  window.toggleSelectAll        = toggleSelectAll;
  window.syncSelectAllHeader    = syncSelectAllHeader;
  window.clearBulkSelection     = clearBulkSelection;
  window.applyBulkAction        = applyBulkAction;
  window.bulkMarkAllAsCompleted = bulkMarkAllAsCompleted;
  window.setViewMode            = setViewMode;
  window.setPageSize            = setPageSize;
  window.copyEmployeeId         = copyEmployeeId;
  window.dismissNotification    = dismissNotification;
})();
