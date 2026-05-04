import re

# Paths
extracted = r'C:\Users\DAVID\Documents\GitHub\Rockstar-Beta\company_system\templates\task_management\personal_board_detail.html.tmp'
final = r'C:\Users\DAVID\Documents\GitHub\Rockstar-Beta\company_system\templates\task_management\personal_board_detail.html'

# Read extracted prefix
with open(extracted, 'r', encoding='utf-8') as f:
    prefix = f.read()

# Define suffix (missing parts)
suffix = '''
// ── Backdrop click to close ──────────────────────────────────────────────────

document.getElementById('addTaskModal').addEventListener('click',    function(e) { if (e.target === this) closeAddTaskModal(); });
document.getElementById('taskDetailModal').addEventListener('click', function(e) { if (e.target === this) closeTaskDetailModal(); });
document.getElementById('helpModal').addEventListener('click',       function(e) { if (e.target === this) toggleHelp(); });

// ── Recurring toggle ─────────────────────────────────────────────────────────

document.getElementById('is_recurring').addEventListener('change', function() {
    document.getElementById('recurring_options').classList.toggle('hidden', !this.checked);
});

// ── Keyboard shortcuts ───────────────────────────────────────────────────────

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeAddTaskModal();
        closeTaskDetailModal();
        document.getElementById('helpModal').classList.remove('show');
    }
    if (e.key === 'n' && !e.target.matches('input, textarea, select')) openAddTaskModal();
    if (e.key === 'r' && !e.target.matches('input, textarea, select')) location.reload();
    if (e.key === 'h' && !e.target.matches('input, textarea, select')) toggleHelp();
});

// ── Drag and drop ────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.personal-column').forEach(function(column) {
        new Sortable(column, {
            group: 'personal',
            animation: 150,
            ghostClass: 'sortable-ghost',
            onEnd: function(evt) {
                var taskId      = evt.item.getAttribute('data-task-id');
                var fromColumnId = evt.from.getAttribute('data-column-id');
                var toColumnId   = evt.to.getAttribute('data-column-id');

                // Optimistically update counts if moving between different columns
                var fromCountEl = null;
                var toCountEl = null;
                if (fromColumnId !== toColumnId) {
                    fromCountEl = document.getElementById('count-col-' + fromColumnId);
                    toCountEl   = document.getElementById('count-col-' + toColumnId);
                    if (fromCountEl) {
                        var currentFrom = parseInt(fromCountEl.textContent) || 0;
                        fromCountEl.textContent = currentFrom - 1;
                    }
                    if (toCountEl) {
                        var currentTo = parseInt(toCountEl.textContent) || 0;
                        toCountEl.textContent = currentTo + 1;
                    }
                }

                fetch('/task/personal/api/update-position/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        task_id: taskId,
                        column_id: toColumnId,
                        order: evt.newIndex
                    })
                })
                .then(function(r) { return r.json(); })
                .catch(function(err) {
                    // If request fails, revert counts to previous state
                    if (fromColumnId !== toColumnId) {
                        if (fromCountEl) {
                            var currentFrom = parseInt(fromCountEl.textContent) || 0;
                            fromCountEl.textContent = currentFrom + 1;
                        }
                        if (toCountEl) {
                            var currentTo = parseInt(toCountEl.textContent) || 0;
                            toCountEl.textContent = currentTo - 1;
                        }
                    }
                    console.error('Failed to update position:', err);
                    showToast('Failed to update position', 'error');
                });
            }
        });
    });
});
</script>
{% endblock %}
'''

# Combine
combined = prefix.rstrip() + '\n' + suffix.lstrip()

# Apply fixes
# 1. Fix isCompleted assignment
combined = combined.replace(
    "var isCompleted = data.is_completed !== undefined ? data.is_completed : (data.success === true);",
    "var isCompleted = data.completed;"
)

# 2. Fix toggleTask fetch headers: replace Content-Type with X-Requested-With and add credentials
old_fetch = """fetch('/task/personal/tasks/' + taskId + '/toggle/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'Content-Type': 'application/json'
    }
})"""
new_fetch = """fetch('/task/personal/tasks/' + taskId + '/toggle/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest'
    },
    credentials: 'same-origin'
})"""
combined = combined.replace(old_fetch, new_fetch)

# Write final file
with open(final, 'w', encoding='utf-8') as f:
    f.write(combined)

print('Final file written with fixes applied.')
