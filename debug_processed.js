>
// ── Global State ────────────────────────────────────────────────────────────────

var isTimelineView = false;
var pendingDeleteChecklistId = null;
var pendingDeleteArchivedId = null;

// ── Utility Functions ──────────────────────────────────────────────────────────

function escapeHtml(str) {
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(str));
    return d.innerHTML;
}

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showToast(message, type) {
    var t = document.getElementById('toast');
    t.textContent = message;
    t.className = 'show ' + (type || 'success');
    clearTimeout(window._toastTimer);
    window._toastTimer = setTimeout(function() { t.className = ''; }, 3000);
}

// ── Task Checklist Initialization ──────────────────────────────────────────────

var taskChecklists = {};


taskChecklists[null] = null;



// ── AJAX Form Submissions ────────────────────────────────────────────────────────

function handleAddTaskFormSubmit(form) {
    var formData = new FormData(form);
    var submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating…';

    fetch(form.action, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast(data.message || 'Task created!', 'success');
            closeAddTaskModal();
            form.reset();
            var countEl = document.getElementById('count-col-' + data.column_id);
            if (countEl) {
                countEl.textContent = parseInt(countEl.textContent || 0) + 1;
            }
            var taskHtml = buildTaskCardHtml(data.task);
            if (!isTimelineView) {
                var columnEl = document.getElementById('column-' + data.column_id);
                if (columnEl) {
                    columnEl.insertAdjacentHTML('beforeend', taskHtml);
                    // Hide "No tasks" placeholder if present
                    var noTasksMsg = columnEl.querySelector('.text-center.py-8');
                    if (noTasksMsg) noTasksMsg.style.display = 'none';
                }
            }
        } else {
            showToast(data.error || 'Failed to create task', 'error');
        }
    })
    .catch(err => {
        showToast('Error: ' + err.message, 'error');
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Task';
    });
    return false;
}

function buildTaskCardHtml(task) {
    var priorityClass = getTaskPriorityClass(task.priority);
    var statusClass = task.is_completed ? 'completed' : '';
    var titleClass = task.is_completed ? 'text-gray-500' : '';
    var checklist = (task.checklist_items || []).map(item => ({
        id: item.id, text: item.text, is_completed: item.is_completed
    }));
    var checklistAttr = 'data-checklist=\'' + escapeHtml(JSON.stringify(checklist)) + '\'';
    var html = '<div class="personal-task rounded-lg p-3 mb-2 ' + statusClass + ' ' + priorityClass + '"' +
        ' data-task-id="' + task.id + '"' +
        ' data-title="' + escapeHtml(task.title) + '"' +
        ' data-priority="' + task.priority + '"' +
        ' data-description="' + escapeHtml(task.description || '') + '"' +
        ' data-deadline="' + (task.deadline || '') + '"' +
        ' data-date-start="' + (task.date_start || '') + '"' +
        ' data-date-end="' + (task.date_end || '') + '"' +
        ' data-notes="' + escapeHtml(task.notes || '') + '"' +
        ' ' + checklistAttr +
        ' draggable="true">';
    html += '<div class="flex justify-between items-start">';
    html += '<button onclick="toggleTask(' + task.id + ')" class="mr-2 mt-1 flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center ' +
        (task.is_completed ? 'bg-green-500 border-green-500' : 'border-gray-300 dark:border-gray-500 hover:border-gray-400 dark:hover:border-gray-300') + '">';
    if (task.is_completed) html += '<i class="fas fa-check text-xs text-white"></i>';
    html += '</button>';
    html += '<div class="flex-1 min-w-0">';
    html += '<h4 onclick="event.stopPropagation(); openTaskDetail(' + task.id + ')" title="Click to edit"' +
        ' class="task-title font-medium text-gray-800 dark:text-gray-100 text-sm ' + titleClass + ' cursor-pointer hover:text-blue-600 dark:hover:text-blue-400">' +
        '<i class="fas fa-edit mr-1 text-gray-500"></i>' + escapeHtml(task.title) + '</h4>';
    if (task.description) {
        html += '<p class="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">' + escapeHtml(task.description) + '</p>';
    }
    html += '<div class="flex items-center gap-2 task-notes">';
    html += '<span class="text-xs px-1.5 py-0.5 rounded ' + getPriorityBadgeClass(task.priority) + '">' + task.priority.charAt(0).toUpperCase() + task.priority.slice(1) + '</span>';
    if (task.is_recurring) {
        html += '<span class="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-400">' +
            '<i class="fas fa-redo mr-1"></i>' + task.recurring_type.charAt(0).toUpperCase() + task.recurring_type.slice(1) + '</span>';
    }
    if (task.deadline) {
        html += '<span class="text-xs text-gray-600 dark:text-gray-400"><i class="fas fa-calendar-alt mr-1"></i>' +
            new Date(task.deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + '</span>';
    }
    if (task.date_start && task.date_end) {
        html += '<span class="text-xs text-blue-600 dark:text-blue-400"><i class="fas fa-calendar-week mr-1"></i>' +
            new Date(task.date_start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' - ' +
            new Date(task.date_end).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + '</span>';
    }
    html += '</div>';
    if (task.notes) {
        html += '<div class="mt-2 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs text-gray-600 dark:text-gray-400">' +
            '<i class="fas fa-sticky-note mr-1"></i>' + escapeHtml(task.notes.substring(0, 50)) + '</div>';
    }
    html += '</div>';
    // Archive button
    html += '<button onclick="archiveTask(' + task.id + ')" class="text-gray-500 dark:text-gray-400 hover:text-yellow-500 dark:hover:text-yellow-400 p-1" title="Archive task">' +
        '<i class="fas fa-archive text-xs"></i></button>';
    html += '</div></div>';
    return html;
}

function handleAddColumnFormSubmit(form) {
    var formData = new FormData(form);
    var submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating…';

    fetch(form.action, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast(data.message || 'Column created!', 'success');
            closeAddColumnModal();
            form.reset();
            // Build column HTML and append to kanban board
            var columnHtml = buildColumnHtml(data.column);
            var kanbanEl = document.getElementById('personalKanban');
            if (kanbanEl) {
                kanbanEl.insertAdjacentHTML('beforeend', columnHtml);
            }
            // Also add new column to add task modal's column select
            var select = document.querySelector('#addTaskModal select[name="column"]');
            if (select) {
                var option = document.createElement('option');
                option.value = data.column.id;
                option.textContent = data.column.name;
                select.appendChild(option);
                select.value = data.column.id; // auto-select new column
            }
        } else {
            showToast(data.error || 'Failed to create column', 'error');
        }
    })
    .catch(err => {
        showToast('Error: ' + err.message, 'error');
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Column';
    });
    return false;
}

function buildColumnHtml(column) {
    var html = '<div class="flex-shrink-0 w-80 min-w-[320px]">';
    html += '<div class="rounded-t-lg px-3 py-3 flex justify-between items-center column-header"';
    html += ' style="background: linear-gradient(90deg, ' + column.color + '20, transparent); border-top: 3px solid ' + column.color + '">';
    html += '<div class="flex items-center gap-2">';
    html += '<span class="w-3 h-3 rounded-full" style="background: ' + column.color + '"></span>';
    html += '<span class="font-semibold text-gray-700 dark:text-gray-200 column-name">' + escapeHtml(column.name) + '</span>';
    html += '<span id="count-col-' + column.id + '" class="text-xs bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded-full text-gray-700 dark:text-gray-300">0</span>';
    html += '</div>';
    html += '<div class="flex items-center gap-1">';
    html += '<button onclick="openAddTaskModal(\'' + column.id + '\')" class="p-1.5 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white" title="Add task">';
    html += '<i class="fas fa-plus text-sm"></i></button>';
    html += '<button onclick="openEditColumnModal(\'' + column.id + '\', \'' + escapeHtml(column.name) + '\', \'' + column.color + '\')" class="p-1.5 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white" title="Edit column">';
    html += '<i class="fas fa-edit text-sm"></i></button>';
    html += '<button onclick="deleteColumn(\'' + column.id + '\')" class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900 text-red-500 hover:text-red-700" title="Delete column">';
    html += '<i class="fas fa-trash text-sm"></i></button>';
    html += '</div></div>';
    html += '<div class="personal-column rounded-b-lg p-2" data-column-id="' + column.id + '" data-column-order="' + column.order + '" data-column-color="' + column.color + '" id="column-' + column.id + '">';
    html += '<div class="text-center py-8 text-gray-600 dark:text-gray-400"><p class="text-sm">No tasks</p></div>';
    html += '</div></div>';
    return html;
}

function getTaskPriorityClass(priority) {
    if (priority === 'urgent') return 'priority-urgent';
    if (priority === 'high') return 'priority-high';
    if (priority === 'medium') return 'priority-medium';
    return 'priority-low';
}

// ── View Mode Toggle ───────────────────────────────────────────────────────────

function toggleViewMode() {
isTimelineView = !isTimelineView;
var kanbanView = document.getElementById('personalKanban');
var timelineView = document.getElementById('timelineView');
var btnText = document.getElementById('viewModeBtnText');

if (isTimelineView) {
kanbanView.classList.add('hidden');
timelineView.classList.remove('hidden');
btnText.textContent = 'Kanban';
renderTimeline();
} else {
kanbanView.classList.remove('hidden');
timelineView.classList.add('hidden');
btnText.textContent = 'Timeline';
}
}

function renderTimeline() {
    var calendarEl = document.getElementById('calendar');
    if (!calendarEl) {
        console.error('Calendar element not found');
        return;
    }
    
    // Safe detection for FullCalendar v6 global
    var Fc = (typeof window !== 'undefined' && window.FullCalendar) ? window.FullCalendar : 
             (typeof FullCalendar !== 'undefined' ? FullCalendar : null);
    if (!Fc) {
        console.error('FullCalendar library not loaded - check static files');
        calendarEl.innerHTML = '<div class="p-4 text-center text-red-500">Calendar library not loaded. Check console.</div>';
        return;
    }
    
    var tasks = [];
    var taskEls = document.querySelectorAll('.personal-task');
    console.log('Total tasks on page:', taskEls.length);
    
    taskEls.forEach(function(taskEl) {
        var dateStart = taskEl.getAttribute('data-date-start');
        var dateEnd = taskEl.getAttribute('data-date-end');
        var deadline = taskEl.getAttribute('data-deadline');
        var title = taskEl.getAttribute('data-title') || 'Untitled';
        var taskId = taskEl.getAttribute('data-task-id');
        
        console.log('Task', taskId, 'start:', dateStart, 'end:', dateEnd, 'deadline:', deadline);
        
        // Determine start and end dates - prefer date_start/date_end, fallback to deadline
        var start, end;
        if (dateStart || dateEnd) {
            start = dateStart || dateEnd;
            end = dateEnd || null;
        } else if (deadline && deadline !== '') {
            start = deadline;
            end = null; // single day event
        } else {
            return; // skip tasks without any dates
        }
        
        var columnEl = taskEl.closest('.personal-column');
        var columnColor = columnEl ? columnEl.getAttribute('data-column-color') : '#6b7280';
        var columnName = 'Column';
        if (columnEl && columnEl.previousElementSibling) {
            var nameEl = columnEl.previousElementSibling.querySelector('.column-name');
            if (nameEl) columnName = nameEl.textContent.trim();
        }
        
        var priority = taskEl.getAttribute('data-priority') || 'medium';
        var isCompleted = taskEl.classList.contains('completed');
        
        tasks.push({
            id: parseInt(taskId),
            title: title,
            start: start,
            end: end,
            backgroundColor: columnColor,
            borderColor: columnColor,
            extendedProps: {
                columnName: columnName,
                priority: priority,
                isCompleted: isCompleted
            }
        });
    });
    
    console.log('Tasks for calendar:', tasks);
    
    if (tasks.length === 0) {
        calendarEl.innerHTML = '<div class="p-4 text-center text-gray-500 dark:text-gray-400">No tasks with date ranges. Add date_start or date_end to tasks to see them here.</div>';
        // Clear any existing calendar
        if (window.personalCalendar) {
            window.personalCalendar.destroy();
            window.personalCalendar = null;
        }
        return;
    }
    
    // Adjust end date inclusivity for FullCalendar (end is exclusive)
    tasks.forEach(function(task) {
        if (task.end && task.end !== null) {
            var endDate = new Date(task.end);
            endDate.setDate(endDate.getDate() + 1);
            task.end = endDate.toISOString().split('T')[0];
        }
    });
    
    // Destroy existing
    if (window.personalCalendar) {
        window.personalCalendar.destroy();
    }
    
    // Initialize calendar
    window.personalCalendar = new Fc.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,listWeek'
        },
        events: tasks,
        eventClick: function(info) {
            openTaskDetail(info.event.id);
        },
        eventContent: function(arg) {
            var columnName = arg.event.extendedProps.columnName || '';
            var priority = arg.event.extendedProps.priority || '';
            return {
                html: '<div class="fc-event-main-content">' +
                      '<div class="font-semibold">' + arg.event.title + '</div>' +
                      '<div class="text-xs" style="opacity:0.8">' + columnName + '</div>' +
                      '</div>'
            };
        },
        eventDidMount: function(info) {
            if (info.event.extendedProps.isCompleted) {
                info.el.style.opacity = '0.5';
                info.el.style.textDecoration = 'line-through';
            }
        },
        height: 'auto',
        themeSystem: 'standard'
    });
    
    window.personalCalendar.render();
}
    


// ── Toast ────────────────────────────────────────────────────────────────────

function showToast(message, type) {
var t = document.getElementById('toast');
t.textContent = message;
t.className = 'show ' + (type || 'success');
clearTimeout(window._toastTimer);
window._toastTimer = setTimeout(function() { t.className = ''; }, 3000);
}

// ── Modal helpers ────────────────────────────────────────────────────────────

function openAddTaskModal(columnId) {
if (columnId) {
var select = document.querySelector('#addTaskModal select[name="column"]');
if (select) select.value = columnId;
}
document.getElementById('addTaskModal').classList.add('show');
}
function closeAddTaskModal() {
document.getElementById('addTaskModal').classList.remove('show');
}
function closeTaskDetailModal() {
    document.getElementById('taskDetailModal').classList.remove('show');
    // Destroy Sortable instance to avoid stale references
    if (window.checklistSortable) {
        window.checklistSortable.destroy();
        window.checklistSortable = null;
    }
}
function toggleHelp() {
    document.getElementById('helpModal').classList.toggle('show');
}

// Column Modal helpers
function openAddColumnModal() {
    document.getElementById('addColumnModal').classList.add('show');
}
function closeAddColumnModal() {
    document.getElementById('addColumnModal').classList.remove('show');
}

function openEditColumnModal(columnId, name, color) {
    document.getElementById('editColumnId').value = columnId;
    document.getElementById('editColumnName').value = name;
    document.getElementById('editColumnColor').value = color;
    document.getElementById('editColumnForm').action = '/task/personal/columns/' + columnId + '/edit/';
    document.getElementById('editColumnModal').classList.add('show');
}

function closeEditColumnModal() {
    document.getElementById('editColumnModal').classList.remove('show');
}

function deleteColumn(columnId) {
    if (confirm('Delete this column? All tasks in this column must be moved or deleted first.')) {
        window.location.href = '/task/personal/columns/' + columnId + '/delete/';
    }
}

// ── Task Detail ──────────────────────────────────────────────────────────────

function openTaskDetail(taskId) {
    console.log('openTaskDetail called with taskId:', taskId);
    var taskEl = document.querySelector('[data-task-id="' + taskId + '"]');
    console.log('taskEl found:', taskEl);
    if (!taskEl) {
        console.warn('Task element not found for ID:', taskId);
        return;
    }

    document.getElementById('detailTaskId').value      = taskId;
    document.getElementById('detailTitle').value       = taskEl.dataset.title       || '';
    document.getElementById('detailDescription').value = taskEl.dataset.description || '';
    document.getElementById('detailPriority').value    = taskEl.dataset.priority    || 'medium';
    document.getElementById('detailDeadline').value    = taskEl.dataset.deadline    || '';
    document.getElementById('detailDateStart').value   = taskEl.dataset.dateStart   || '';
    document.getElementById('detailDateEnd').value     = taskEl.dataset.dateEnd     || '';
    document.getElementById('detailNotes').value       = taskEl.dataset.notes       || '';

    document.getElementById('updateTaskForm').action = '/task/personal/tasks/' + taskId + '/edit/';

    loadChecklistItems(taskId);
    document.getElementById('taskDetailModal').classList.add('show');
}

// ── Checklist rendering ──────────────────────────────────────────────────────

function renderChecklistItem(item) {
    var checked = item.is_completed ? 'checked' : '';
    var textColor = item.is_completed ? 'text-gray-500 dark:text-gray-400' : 'text-gray-800 dark:text-white';
    var html = '<div class="flex items-center gap-2 p-2 rounded bg-gray-100 dark:bg-gray-700/50" id="checklist-item-' + item.id + '" data-item-id="' + item.id + '">';
    html += '<button type="button" class="drag-handle cursor-grab active:cursor-grabbing p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" title="Drag to reorder">';
    html += '<i class="fas fa-grip-vertical text-xs"></i>';
    html += '</button>';
    html += '<input type="checkbox" ' + checked + ' onchange="toggleChecklist(' + item.id + ', this)" class="w-4 h-4">';
    html += '<span class="flex-1 text-sm ' + textColor + '" contenteditable="true" onblur="renameChecklist(' + item.id + ', this)" onkeydown="if(event.key===\'Enter\'){event.preventDefault();this.blur();}" title="Click to rename">' + escapeHtml(item.text) + '</span>';
    html += '<button type="button" onclick="openDeleteChecklistModal(' + item.id + ')" class="text-gray-500 dark:text-gray-400 hover:text-red-400 dark:hover:text-red-500 flex-shrink-0" title="Delete">';
    html += '<i class="fas fa-trash text-xs"></i>';
    html += '</button>';
    html += '</div>';
    return html;
}

function escapeHtml(str) {
var d = document.createElement('div');
d.appendChild(document.createTextNode(str));
return d.innerHTML;
}

// ── Inline checklist rename ────────────────────────────────────────────────────

function renameChecklist(itemId, spanEl) {
    var newText = spanEl.textContent.trim();
    if (!newText) {
        // Revert to original from cache
        var taskId = document.getElementById('detailTaskId').value;
        var originalItem = taskChecklists[taskId] && taskChecklists[taskId].find(function(i) { return i.id === itemId; });
        if (originalItem) {
            spanEl.textContent = originalItem.text;
        } else {
            spanEl.textContent = 'Untitled';
        }
        return;
    }
    
    fetch('/task/personal/checklist/' + itemId + '/rename/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: 'text=' + encodeURIComponent(newText)
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            var taskId = document.getElementById('detailTaskId').value;
            if (taskChecklists[taskId]) {
                taskChecklists[taskId] = taskChecklists[taskId].map(function(i) {
                    return i.id === itemId ? Object.assign({}, i, { text: newText }) : i;
                });
            }
            var taskEl = document.querySelector('[data-task-id="' + taskId + '"]');
            if (taskEl) {
                var checklist = JSON.parse(taskEl.dataset.checklist || '[]');
                checklist = checklist.map(function(i) {
                    return i.id === itemId ? Object.assign({}, i, { text: newText }) : i;
                });
                taskEl.dataset.checklist = JSON.stringify(checklist);
            }
        } else {
            showToast(data.error || 'Rename failed', 'error');
            var taskId = document.getElementById('detailTaskId').value;
            var originalItem = taskChecklists[taskId] && taskChecklists[taskId].find(function(i) { return i.id === itemId; });
            if (originalItem) {
                spanEl.textContent = originalItem.text;
            }
        }
    })
    .catch(function(err) {
        showToast('Failed to rename: ' + err.message, 'error');
    });
}

function loadChecklistItems(taskId) {
    var container = document.getElementById('checklistItems');
    if (!container) return;

    var taskEl = document.querySelector('[data-task-id="' + taskId + '"]');
    if (!taskEl) {
        container.innerHTML = '<p class="text-gray-600 dark:text-gray-400 text-sm py-2">Task not found.</p>';
        return;
    }

    var items = [];
    var checklistData = taskEl.getAttribute('data-checklist');
    if (checklistData) {
        try {
            items = JSON.parse(checklistData);
        } catch(e) {
            console.error('Failed to parse checklist data:', e);
        }
    }

    // Keep cache in sync (optional)
    taskChecklists[taskId] = items;

    if (!items || items.length === 0) {
        container.innerHTML = '<p class="text-gray-600 dark:text-gray-400 text-sm py-2">No checklist items yet.</p>';
    } else {
        container.innerHTML = items.map(renderChecklistItem).join('');
    }

    // Initialize Sortable for drag and drop
    if (window.checklistSortable) {
        window.checklistSortable.destroy();
        window.checklistSortable = null;
    }
    
    window.checklistSortable = new Sortable(container, {
        handle: '.drag-handle',
        animation: 150,
        chosenClass: 'chosen-checklist-item',
        dragClass: 'opacity-50',
        onEnd: function (evt) {
            var taskId = document.getElementById('detailTaskId').value;
            var itemId = evt.item.dataset.itemId;
            
            // Update taskChecklists array
            if (taskChecklists[taskId]) {
                // Move the item to its new position
                var movedItem = taskChecklists[taskId].splice(evt.oldIndex, 1)[0];
                taskChecklists[taskId].splice(evt.newIndex, 0, movedItem);
                
                // Update the data-checklist attribute on the card
                var taskEl = document.querySelector('[data-task-id="' + taskId + '"]');
                if (taskEl) {
                    try {
                        var checklist = JSON.parse(taskEl.getAttribute('data-checklist') || '[]');
                        // Reorder the checklist array to match the new DOM order
                        var newOrder = Array.from(container.children)
                            .map(child => parseInt(child.dataset.itemId))
                            .filter(id => !isNaN(id));
                        
                        var reorderedChecklist = newOrder.map(id => 
                            checklist.find(item => item.id === id)
                        ).filter(Boolean);
                        
                        taskEl.setAttribute('data-checklist', JSON.stringify(reorderedChecklist));
                    } catch(e) {
                        console.error('Failed to update checklist order:', e);
                    }
                }
            }
        }
    });
}

// ── Submit checklist item (AJAX — uses real server ID from response) ─────────

function submitChecklist() {
    var taskId = document.getElementById('detailTaskId').value;
    var input  = document.getElementById('checklistInput');
    var text   = (input.value || '').trim();
    if (!text || !taskId) return;

    input.disabled = true;

    fetch('/task/personal/tasks/' + taskId + '/checklist/add/', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: 'checklist_text=' + encodeURIComponent(text) + '&csrfmiddlewaretoken=' + getCookie('csrftoken')
    })
    .then(function(r) {
        if (!r.ok) throw new Error('Server error ' + r.status);
        return r.json();
    })
    .then(function(data) {
        if (!data.id) throw new Error('Server did not return item id');

        var container = document.getElementById('checklistItems');
        var noItems = container.querySelector('p');
        if (noItems) noItems.remove();

        var newItem = { id: data.id, text: data.text || text, is_completed: false };
        container.insertAdjacentHTML('beforeend', renderChecklistItem(newItem));

        // Update taskChecklists[taskId] array
        if (!taskChecklists[taskId]) {
            taskChecklists[taskId] = [];
        }
        taskChecklists[taskId].push(newItem);

        // Update the data-checklist attribute on the card
        var taskEl = document.querySelector('[data-task-id="' + taskId + '"]');
        if (taskEl) {
            var existingChecklist = taskEl.getAttribute('data-checklist') || '';
            var checklist = [];
            try {
                if (existingChecklist.trim()) {
                    checklist = JSON.parse(existingChecklist);
                    if (!Array.isArray(checklist)) checklist = [];
                }
            } catch(e) { 
                checklist = []; 
            }
            checklist.push(newItem);
            taskEl.setAttribute('data-checklist', JSON.stringify(checklist));
        }

        input.value = '';
        showToast('Checklist item added', 'success');
    })
    .catch(function(err) {
        showToast('Failed to add item: ' + err.message, 'error');
    })
    .finally(function() {
        input.disabled = false;
        input.focus();
    });
}

// ── Toggle checklist item ────────────────────────────────────────────────────

function toggleChecklist(itemId, checkbox) {
    console.log('toggleChecklist called, itemId:', itemId);
    fetch('/task/personal/checklist/' + itemId + '/toggle/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
        }
    })
    .then(function(r) {
        if (!r.ok) throw new Error('Toggle failed');
        return r.json();
    })
    .then(function(data) {
        console.log('Toggle response:', data);
        var row  = document.getElementById('checklist-item-' + itemId);
        if (!row) return;
        var span = row.querySelector('span');
        var cb   = row.querySelector('input[type="checkbox"]');
        var done = data.completed;
        if (cb)   cb.checked = done;
        if (span) span.className = 'flex-1 text-sm ' + (done ? 'text-gray-500 dark:text-gray-400' : 'text-gray-800 dark:text-white');

        // Get taskId from the currently open modal
        var taskId = document.getElementById('detailTaskId').value;
        console.log('Current modal taskId:', taskId);
        console.log('taskChecklists before update:', JSON.stringify(taskChecklists[taskId]));

        // Update taskChecklists array
        if (taskChecklists[taskId]) {
            taskChecklists[taskId] = taskChecklists[taskId].map(function(i) {
                return i.id === itemId ? Object.assign({}, i, { is_completed: done }) : i;
            });
            console.log('taskChecklists after update:', JSON.stringify(taskChecklists[taskId]));
        }

        // Also update data-checklist on card
        var taskEl = document.querySelector('[data-task-id="' + taskId + '"]');
        if (taskEl) {
            try {
                var checklist = JSON.parse(taskEl.dataset.checklist || '[]');
                checklist = checklist.map(function(i) {
                    return i.id === itemId ? Object.assign({}, i, { is_completed: done }) : i;
                });
                taskEl.dataset.checklist = JSON.stringify(checklist);
                console.log('Updated data-checklist on card:', taskEl.dataset.checklist);
            } catch(e) {}
        }
    })
    .catch(function() {
        // Revert checkbox on failure
        if (checkbox) checkbox.checked = !checkbox.checked;
        showToast('Toggle failed', 'error');
    });
}

// ── Save Task (AJAX) ─────────────────────────────────────────────────────────

function saveTask() {
    var taskId  = document.getElementById('detailTaskId').value;
    var saveBtn = document.getElementById('saveBtn');
    if (!taskId) return;

    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving…';

    var formData = new FormData();
    formData.append('title',       document.getElementById('detailTitle').value);
    formData.append('description', document.getElementById('detailDescription').value);
    formData.append('priority',    document.getElementById('detailPriority').value);
    formData.append('deadline',    document.getElementById('detailDeadline').value);
    formData.append('date_start',  document.getElementById('detailDateStart').value);
    formData.append('date_end',    document.getElementById('detailDateEnd').value);
    formData.append('notes',       document.getElementById('detailNotes').value);
    formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

    fetch('/task/personal/tasks/' + taskId + '/edit/', {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: formData
    })
    .then(function(r) {
        if (!r.ok) throw new Error('Server error ' + r.status);
        return r.json();
    })
    .then(function(data) {
        if (data.success) {
            showToast('Task saved successfully', 'success');
            // Update the task card in the kanban view
            var taskEl = document.querySelector('[data-task-id="' + taskId + '"]');
            if (taskEl) {
                taskEl.dataset.title = data.title || '';
                taskEl.dataset.description = data.description || '';
                taskEl.dataset.priority = data.priority || 'medium';
                taskEl.dataset.deadline = data.deadline || '';
                taskEl.dataset.dateStart = data.date_start || '';
                taskEl.dataset.dateEnd = data.date_end || '';
                taskEl.dataset.notes = data.notes || '';
                
                // Update UI
                var titleEl = taskEl.querySelector('.task-title');
                if (titleEl) titleEl.textContent = data.title || '';
                
                var descEl = taskEl.querySelector('.text-xs.text-gray-600.dark\\:text-gray-400.mt-1.line-clamp-2');
                if (descEl) descEl.textContent = data.description || '';
                
                // Update priority badge
                var prioritySpan = taskEl.querySelector('.task-notes span:first-child');
                if (prioritySpan) {
                    prioritySpan.className = 'text-xs px-1.5 py-0.5 rounded ' +
                        (data.priority == 'urgent' ? 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400' :
                         data.priority == 'high' ? 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-400' :
                         data.priority == 'medium' ? 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400' :
                         'bg-gray-100 text-gray-700 dark:bg-gray-500/20 dark:text-gray-400');
                    prioritySpan.textContent = (data.priority || 'medium').charAt(0).toUpperCase() + (data.priority || 'medium').slice(1);
                }
                
                // Update dates
                var dateSpan = taskEl.querySelector('.task-notes span:not(:first-child):not(:last-child)');
                if (dateSpan) {
                    if (data.date_start && data.date_end) {
                        dateSpan.innerHTML = '<i class="fas fa-calendar-week mr-1"></i>' + 
                            new Date(data.date_start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + 
                            ' - ' + new Date(data.date_end).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                        dateSpan.className = 'text-xs text-blue-600 dark:text-blue-400';
                    } else if (data.deadline) {
                        dateSpan.innerHTML = '<i class="fas fa-calendar-alt mr-1"></i>' + 
                            new Date(data.deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                        dateSpan.className = 'text-xs text-gray-600 dark:text-gray-400';
                    }
                }
                
                // Update completion status safely
                var toggleBtn = taskEl.querySelector('button[onclick^="toggleTask"]');
                var toggleIcon = toggleBtn ? toggleBtn.querySelector('i') : null;
                var titleEl = taskEl.querySelector('.task-title');
                if (data.is_completed) {
                    taskEl.classList.add('completed');
                    if (toggleBtn) {
                        toggleBtn.classList.add('bg-green-500', 'border-green-500');
                        if (!toggleIcon) {
                            toggleIcon = document.createElement('i');
                            toggleIcon.className = 'fas fa-check text-xs text-white';
                            toggleBtn.appendChild(toggleIcon);
                        } else {
                            toggleIcon.classList.add('fas', 'fa-check', 'text-xs', 'text-white');
                        }
                    }
                    if (titleEl) titleEl.classList.add('text-gray-500');
                } else {
                    taskEl.classList.remove('completed');
                    if (toggleBtn) {
                        toggleBtn.classList.remove('bg-green-500', 'border-green-500');
                        if (toggleIcon) {
                            toggleIcon.remove();
                        }
                    }
                    if (titleEl) titleEl.classList.remove('text-gray-500');
                }
                
                // Update priority border
                ['priority-low', 'priority-medium', 'priority-high', 'priority-urgent'].forEach(function(cls) {
                    taskEl.classList.remove(cls);
                });
                if (data.priority) {
                    taskEl.classList.add('priority-' + data.priority);
                }
                
                // Update checklist
                 taskEl.dataset.checklist = JSON.stringify(data.checklist_items || []);
                 loadChecklistItems(taskId); // Reload checklist with updated data
             }
             
             // Close modal after successful save
             closeTaskDetailModal();
             
             // Refresh timeline if currently viewing it
             if (isTimelineView && window.personalCalendar) {
                 renderTimeline();
             }
         } else {
             showToast(data.error || 'Save failed', 'error');
         }
     })
     .catch(function(err) {
         showToast('Failed to save: ' + err.message, 'error');
     })
     .finally(function() {
         saveBtn.disabled = false;
         saveBtn.textContent = 'Save Changes';
     });
 }

// ── Other task actions ───────────────────────────────────────────────────────

function toggleTask(taskId) {
    var taskEl = document.querySelector('[data-task-id="' + taskId + '"]');
    var checkboxBtn = taskEl ? taskEl.querySelector('button[onclick*="toggleTask"]') : null;

    fetch('/task/personal/tasks/' + taskId + '/toggle/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
        }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        console.log('Toggle response:', data);
        if (data.success !== false) {
            var taskEl = document.querySelector('[data-task-id="' + taskId + '"]');
            if (!taskEl) return;

            // Check both success and is_completed, or just use is_completed if success is undefined
            var isCompleted = data.completed;

            // Toggle completed class
            if (isCompleted) {
                taskEl.classList.add('completed');
                // Remove priority class when completed (it shows green border)
                taskEl.classList.remove('priority-low', 'priority-medium', 'priority-high', 'priority-urgent');
            } else {
                taskEl.classList.remove('completed');
                // Re-add priority class based on data-priority attribute
                var priority = taskEl.dataset.priority || 'medium';
                taskEl.classList.remove('priority-low', 'priority-medium', 'priority-high', 'priority-urgent');
                taskEl.classList.add('priority-' + priority);
            }

            // Update checkbox button
            var checkboxBtn = taskEl.querySelector('button[onclick*="toggleTask"]');
            if (checkboxBtn) {
                checkboxBtn.innerHTML = isCompleted ? '<i class="fas fa-check text-xs text-white"></i>' : '';
                checkboxBtn.className = 'mr-2 mt-1 flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center ' + 
                (isCompleted ? 'bg-green-500 border-green-500' : 'border-gray-300 dark:border-gray-500 hover:border-gray-400 dark:hover:border-gray-300');
            }

            // Update task title styling
            var titleEl = taskEl.querySelector('h4.task-title');
            if (titleEl) {
                if (isCompleted) {
                    titleEl.classList.add('text-gray-500');
                    titleEl.classList.remove('text-gray-800');
                } else {
                    titleEl.classList.remove('text-gray-500');
                    titleEl.classList.add('text-gray-800');
                }
            }

            // Refresh timeline if showing
            if (isTimelineView && window.personalCalendar) {
                renderTimeline();
            }

            showToast(isCompleted ? 'Task completed!' : 'Task marked incomplete', 'success');
        } else {
            showToast('Failed to update task: ' + (data.message || 'Unknown error'), 'error');
        }
    })
    .catch(function(err) {
        console.error('Toggle error:', err);
        showToast('Failed to update task: ' + err.message, 'error');
    });
}



// ── Archived Tasks ─────────────────────────────────────────────────────────────

function showArchivedTasks() {
    var drawer = document.getElementById('archivedDrawer');
    var backdrop = document.getElementById('archivedBackdrop');
    drawer.classList.remove('translate-x-full');
    backdrop.classList.remove('hidden');
}

function closeArchivedTasks() {
    document.getElementById('archivedDrawer').classList.add('translate-x-full');
    document.getElementById('archivedBackdrop').classList.add('hidden');
}



function getPriorityBadgeClass(priority) {
    if (priority === 'urgent') return 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400';
    if (priority === 'high') return 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-400';
    if (priority === 'medium') return 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400';
    return 'bg-gray-100 text-gray-700 dark:bg-gray-500/20 dark:text-gray-400';
}

function restoreTask(taskId) {
    if (!confirm('Restore this task?')) return;
    fetch('/task/personal/tasks/' + taskId + '/restore/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('Task restored', 'success');
            var taskEl = document.querySelector('#archivedTasksList [data-task-id="' + taskId + '"]');
            if (taskEl) taskEl.remove();
            updateArchivedCount(-1);
            if (document.querySelectorAll('#archivedTasksList [data-task-id]').length === 0) {
                document.getElementById('archivedTasksList').innerHTML = '<div class="text-center py-8 text-gray-600 dark:text-gray-400"><p class="text-sm">No archived tasks</p></div>';
            }
            // Re-insert task into its column
            if (data.task && data.task.column_id) {
                var taskHtml = buildTaskCardHtml(data.task);
                var columnEl = document.getElementById('column-' + data.task.column_id);
                if (columnEl) {
                    columnEl.insertAdjacentHTML('beforeend', taskHtml);
                    var noTasksMsg = columnEl.querySelector('.text-center.py-8');
                    if (noTasksMsg) noTasksMsg.style.display = 'none';
                    var countEl = document.getElementById('count-col-' + data.task.column_id);
                    if (countEl) {
                        countEl.textContent = parseInt(countEl.textContent || 0) + 1;
                    }
                }
            }
        } else {
            showToast('Restore failed', 'error');
        }
    })
    .catch(err => {
        showToast('Failed: ' + err.message, 'error');
    });
}

function openDeleteArchivedModal(taskId) {
    pendingDeleteArchivedId = taskId;
    document.getElementById('deleteArchivedModal').classList.add('show');
}

function closeDeleteArchivedModal() {
    document.getElementById('deleteArchivedModal').classList.remove('show');
    pendingDeleteArchivedId = null;
}

// Confirm delete button
document.getElementById('confirmDeleteArchivedBtn').addEventListener('click', function() {
    if (!pendingDeleteArchivedId) return;
    fetch('/task/personal/tasks/' + pendingDeleteArchivedId + '/delete/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('Task deleted permanently', 'success');
            var taskEl = document.querySelector('#archivedTasksList [data-task-id="' + pendingDeleteArchivedId + '"]');
            if (taskEl) taskEl.remove();
            updateArchivedCount(-1);
            if (document.querySelectorAll('#archivedTasksList [data-task-id]').length === 0) {
                document.getElementById('archivedTasksList').innerHTML = '<div class="text-center py-8 text-gray-600 dark:text-gray-400"><p class="text-sm">No archived tasks</p></div>';
            }
            closeDeleteArchivedModal();
        } else {
            showToast('Delete failed', 'error');
        }
    })
    .catch(err => {
        showToast('Failed: ' + err.message, 'error');
    });
});

function archiveTask(taskId) {
    if (!confirm('Archive this task?')) return;
    var taskEl = document.querySelector('[data-task-id="' + taskId + '"]');
    if (!taskEl) return;
    // Gather task data before removing
    var taskData = {
        id: parseInt(taskId),
        title: taskEl.dataset.title || '',
        description: taskEl.dataset.description || '',
        priority: taskEl.dataset.priority || 'medium',
        deadline: taskEl.dataset.deadline || '',
        is_completed: taskEl.classList.contains('completed')
    };
    fetch('/task/personal/tasks/' + taskId + '/archive/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success || data.archived) {
            showToast('Task archived', 'success');
            taskEl.remove();
            var columnEl = taskEl.closest('.personal-column');
            if (columnEl) {
                var columnId = columnEl.getAttribute('data-column-id');
                var countEl = document.getElementById('count-col-' + columnId);
                if (countEl) {
                    var count = parseInt(countEl.textContent) || 0;
                    countEl.textContent = count - 1;
                    // Show "No tasks" placeholder if column is empty
                    if (count - 1 === 0) {
                        var noTasksMsg = columnEl.querySelector('.text-center.py-8');
                        if (!noTasksMsg) {
                            noTasksMsg = document.createElement('div');
                            noTasksMsg.className = 'text-center py-8 text-gray-600 dark:text-gray-400';
                            noTasksMsg.innerHTML = '<p class="text-sm">No tasks</p>';
                            columnEl.appendChild(noTasksMsg);
                        } else {
                            noTasksMsg.style.display = 'block';
                        }
                    }
                }
            }
            updateArchivedCount(1);
            prependArchivedTask(taskData);
        } else {
            showToast('Archive failed', 'error');
        }
    })
    .catch(err => {
        showToast('Failed: ' + err.message, 'error');
    });
}

function archiveDetailTask() {
    var taskId = document.getElementById('detailTaskId').value;
    if (!taskId) return;
    if (!confirm('Archive this task?')) return;
    var taskEl = document.querySelector('[data-task-id="' + taskId + '"]');
    var taskData = taskEl ? {
        id: parseInt(taskId),
        title: taskEl.dataset.title || '',
        description: taskEl.dataset.description || '',
        priority: taskEl.dataset.priority || 'medium',
        deadline: taskEl.dataset.deadline || '',
        is_completed: taskEl.classList.contains('completed')
    } : null;
    fetch('/task/personal/tasks/' + taskId + '/archive/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success || data.archived) {
            showToast('Task archived', 'success');
            closeTaskDetailModal();
            if (taskEl) taskEl.remove();
            var columnEl = taskEl ? taskEl.closest('.personal-column') : null;
            if (columnEl) {
                var columnId = columnEl.getAttribute('data-column-id');
                var countEl = document.getElementById('count-col-' + columnId);
                if (countEl) {
                    var newCount = Math.max(0, (parseInt(countEl.textContent) || 0) - 1);
                    countEl.textContent = newCount;
                    // Show "No tasks" placeholder if column becomes empty
                    if (newCount === 0) {
                        var noTasksMsg = columnEl.querySelector('.text-center.py-8');
                        if (!noTasksMsg) {
                            noTasksMsg = document.createElement('div');
                            noTasksMsg.className = 'text-center py-8 text-gray-600 dark:text-gray-400';
                            noTasksMsg.innerHTML = '<p class="text-sm">No tasks</p>';
                            columnEl.appendChild(noTasksMsg);
                        } else {
                            noTasksMsg.style.display = 'block';
                        }
                    }
                }
            }
            updateArchivedCount(1);
            if (taskData) prependArchivedTask(taskData);
        } else {
            showToast('Archive failed', 'error');
        }
    })
    .catch(err => {
        showToast('Failed: ' + err.message, 'error');
    });
}

function updateArchivedCount(delta) {
    var badge = document.getElementById('archivedCountBadge');
    var current = parseInt(badge.textContent) || 0;
    var newCount = current + delta;
    if (newCount > 0) {
        badge.textContent = newCount;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

function prependArchivedTask(task) {
    var container = document.getElementById('archivedTasksList');
    // Remove empty message if present
    var emptyMsg = container.querySelector('.text-center');
    if (emptyMsg) emptyMsg.remove();

    var priorityClass = getPriorityBorderClass(task.priority);
    var dateStr = task.deadline ? new Date(task.deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '';
    var html = '<div class="p-3 mb-2 rounded-lg border-l-4 ' + priorityClass + '" data-task-id="' + task.id + '">' +
        '<div class="flex justify-between items-start">' +
        '<div class="flex-1 min-w-0">' +
        '<h4 class="font-medium text-gray-800 dark:text-gray-100 text-sm' + (task.is_completed ? ' text-gray-500' : '') + '">' + escapeHtml(task.title) + '</h4>' +
        (task.description ? '<p class="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">' + escapeHtml(task.description) + '</p>' : '') +
        '<div class="flex items-center gap-2 mt-2">' +
        '<span class="text-xs px-1.5 py-0.5 rounded ' + getPriorityBadgeClass(task.priority) + '">' + task.priority.charAt(0).toUpperCase() + task.priority.slice(1) + '</span>' +
        (dateStr ? '<span class="text-xs text-gray-600 dark:text-gray-400"><i class="fas fa-calendar-alt mr-1"></i>' + dateStr + '</span>' : '') +
        '</div></div>' +
        '<div class="flex items-center gap-2 flex-shrink-0">' +
        '<button onclick="restoreTask(' + task.id + ')" class="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700" title="Restore task">' +
        '<i class="fas fa-undo mr-1"></i>Restore</button>' +
        '<button onclick="openDeleteArchivedModal(' + task.id + ')" class="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700" title="Delete permanently">' +
        '<i class="fas fa-trash mr-1"></i>Delete</button>' +
        '</div></div>';
    container.insertAdjacentHTML('afterbegin', html);
}

function getPriorityBorderClass(priority) {
    if (priority === 'urgent') return 'bg-red-50 dark:bg-red-900/20 border-red-500';
    if (priority === 'high') return 'bg-orange-50 dark:bg-orange-900/20 border-orange-500';
    if (priority === 'medium') return 'bg-blue-50 dark:bg-blue-900/20 border-blue-500';
    return 'bg-gray-50 dark:bg-gray-700/50 border-gray-400';
}



// ── CSRF helper ──────────────────────────────────────────────────────────────

function getCookie(name) {
var cookieValue = null;
if (document.cookie && document.cookie !== '') {
var cookies = document.cookie.split(';');
for (var i = 0; i < cookies.length; i++) {
var cookie = cookies[i].trim();
if (cookie.substring(0, name.length + 1) === (name + '=')) {
cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
break;
}
}
}
return cookieValue;
}

// ── Backdrop click to close ──────────────────────────────────────────────────

document.getElementById('addTaskModal').addEventListener('click',    function(e) { if (e.target === this) closeAddTaskModal(); });
document.getElementById('taskDetailModal').addEventListener('click', function(e) { if (e.target === this) closeTaskDetailModal(); });
document.getElementById('helpModal').addEventListener('click',       function(e) { if (e.target === this) toggleHelp(); });
document.getElementById('addColumnModal').addEventListener('click',  function(e) { if (e.target === this) closeAddColumnModal(); });
document.getElementById('editColumnModal').addEventListener('click',  function(e) { if (e.target === this) closeEditColumnModal(); });
document.getElementById('deleteChecklistModal').addEventListener('click', function(e) { if (e.target === this) closeDeleteChecklistModal(); });
document.getElementById('deleteArchivedModal').addEventListener('click', function(e) { if (e.target === this) closeDeleteArchivedModal(); });

// ── AJAX form submissions ────────────────────────────────────────────────────

document.getElementById('addTaskForm').addEventListener('submit', function(e) {
    e.preventDefault();
    return handleAddTaskFormSubmit(this);
});

document.getElementById('addColumnForm').addEventListener('submit', function(e) {
    e.preventDefault();
    return handleAddColumnFormSubmit(this);
});

// ── Recurring toggle ─────────────────────────────────────────────────────────

document.getElementById('is_recurring').addEventListener('change', function() {
    document.getElementById('recurring_options').classList.toggle('hidden', !this.checked);
});

// ── Delete checklist confirmation ──────────────────────────────────────────────

function openDeleteChecklistModal(itemId) {
    pendingDeleteChecklistId = itemId;
    document.getElementById('deleteChecklistModal').classList.add('show');
}

function closeDeleteChecklistModal() {
    document.getElementById('deleteChecklistModal').classList.remove('show');
    pendingDeleteChecklistId = null;
}

function openDeleteArchivedModal(taskId) {
    pendingDeleteArchivedId = taskId;
    document.getElementById('deleteArchivedModal').classList.add('show');
}

function closeDeleteArchivedModal() {
    document.getElementById('deleteArchivedModal').classList.remove('show');
    pendingDeleteArchivedId = null;
}

function deleteArchivedTask(taskId) {
    fetch('/task/personal/tasks/' + taskId + '/delete/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast('Task deleted permanently', 'success');
            var taskEl = document.querySelector('#archivedTasksList [data-task-id="' + taskId + '"]');
            if (taskEl) taskEl.remove();
            updateArchivedCount(-1);
            if (document.querySelectorAll('#archivedTasksList [data-task-id]').length === 0) {
                document.getElementById('archivedTasksList').innerHTML = '<div class="text-center py-8 text-gray-600 dark:text-gray-400"><p class="text-sm">No archived tasks</p></div>';
            }
            closeDeleteArchivedModal();
        } else {
            showToast('Delete failed', 'error');
        }
    })
    .catch(err => {
        showToast('Failed: ' + err.message, 'error');
    });
}

// Delete confirmation button
document.getElementById('confirmDeleteChecklistBtn').addEventListener('click', function() {
    if (!pendingDeleteChecklistId) return;
    
    fetch('/task/personal/checklist/' + pendingDeleteChecklistId + '/delete/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            var itemEl = document.getElementById('checklist-item-' + pendingDeleteChecklistId);
            if (itemEl) itemEl.remove();
            
            var taskId = document.getElementById('detailTaskId').value;
            if (taskChecklists[taskId]) {
                taskChecklists[taskId] = taskChecklists[taskId].filter(function(i) {
                    return i.id !== pendingDeleteChecklistId;
                });
            }
            
            var taskEl = document.querySelector('[data-task-id="' + taskId + '"]');
            if (taskEl) {
                var checklist = JSON.parse(taskEl.dataset.checklist || '[]');
                checklist = checklist.filter(function(i) { return i.id !== pendingDeleteChecklistId; });
                taskEl.dataset.checklist = JSON.stringify(checklist);
            }
            
            var container = document.getElementById('checklistItems');
            if (container && container.querySelectorAll('.flex.items-center').length === 0) {
                container.innerHTML = '<p class="text-gray-500 text-sm py-2">No checklist items yet.</p>';
            }
            
            closeDeleteChecklistModal();
            showToast('Item deleted', 'success');
        } else {
            showToast('Delete failed', 'error');
        }
    })
    .catch(function(err) {
        showToast('Failed to delete: ' + err.message, 'error');
    });
});

// Confirm delete archived task
document.getElementById('confirmDeleteArchivedBtn').addEventListener('click', function() {
    if (!pendingDeleteArchivedId) return;
    deleteArchivedTask(pendingDeleteArchivedId);
});

// ── Checklist drag & drop ─────────────────────────────────────────────────────

function initChecklistSortable() {
    var container = document.getElementById('checklistItems');
    if (!container || window.checklistSortable) return;

    window.checklistSortable = new Sortable(container, {
        animation: 150,
        handle: '.drag-handle',
        ghostClass: 'sortable-ghost',
        onEnd: function(evt) {
            var itemId = parseInt(evt.item.getAttribute('data-item-id'));
            var newOrder = evt.newIndex;
            var taskId = document.getElementById('detailTaskId').value;
            
            // Update local order immediately
            if (taskChecklists[taskId]) {
                var item = taskChecklists[taskId].splice(evt.oldIndex, 1)[0];
                taskChecklists[taskId].splice(newOrder, 0, item);
            }
            
            // Persist order to server
            fetch('/task/personal/tasks/' + taskId + '/checklist/reorder/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    item_id: itemId,
                    order: newOrder
                })
            })
            .then(function(r) { return r.json(); })
            .catch(function(err) {
                console.error('Failed to update order:', err);
                showToast('Failed to update order', 'error');
            });
        }
    });
}

// ── Keyboard shortcuts ───────────────────────────────────────────────────────

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeAddTaskModal();
        closeTaskDetailModal();
        closeEditColumnModal();
        closeDeleteChecklistModal();
        closeDeleteArchivedModal();
        closeArchivedTasks();
        document.getElementById('helpModal').classList.remove('show');
    }
    if (e.key === 'n' && !e.target.matches('input, textarea, select')) openAddTaskModal();
    if (e.key === 'r' && !e.target.matches('input, textarea, select')) location.reload();
    if (e.key === 'h' && !e.target.matches('input, textarea, select')) toggleHelp();
});

// ── Edit Column Form Submit ─────────────────────────────────────────────────────

document.getElementById('editColumnForm').addEventListener('submit', function(e) {
    e.preventDefault();
    var columnId = document.getElementById('editColumnId').value;
    var name = document.getElementById('editColumnName').value;
    var color = document.getElementById('editColumnColor').value;
    
    fetch('/task/personal/columns/' + columnId + '/edit/', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: 'name=' + encodeURIComponent(name) + '&color=' + encodeURIComponent(color)
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        console.log('Edit response:', data);
        if (data.success) {
            // Update column header name
            var colHeader = document.querySelector('[data-column-id="' + columnId + '"]').closest('.flex-shrink-0').querySelector('.column-name');
            if (colHeader) colHeader.textContent = data.name;
            // Update column header colors
            var colHeaderDiv = document.querySelector('[data-column-id="' + columnId + '"]').closest('.flex-shrink-0').querySelector('.column-header');
            if (colHeaderDiv) {
                var headerColor = data.color;
                colHeaderDiv.style.background = 'linear-gradient(90deg, ' + headerColor + '20, transparent)';
                colHeaderDiv.style.borderTop = '3px solid ' + headerColor;
                // Update color circle
                var colorCircle = colHeaderDiv.querySelector('.rounded-full');
                if (colorCircle) colorCircle.style.background = headerColor;
            }
            closeEditColumnModal();
            showToast('Column updated!', 'success');
        } else {
            showToast('Update failed: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(function(err) {
        console.error('Edit error:', err);
        showToast('Update failed: ' + err.message, 'error');
    });
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

                // Update "No tasks" message visibility
                var fromColumnBody = document.getElementById('column-' + fromColumnId);
                var toColumnBody = document.getElementById('column-' + toColumnId);
                
                if (fromColumnBody) {
                    var fromTasks = fromColumnBody.querySelectorAll('.personal-task');
                    var fromNoTasks = fromColumnBody.querySelector('.text-center.py-8');
                    if (fromNoTasks) {
                        fromNoTasks.style.display = fromTasks.length === 0 ? 'block' : 'none';
                    }
                }
                if (toColumnBody) {
                    var toTasks = toColumnBody.querySelectorAll('.personal-task');
                    var toNoTasks = toColumnBody.querySelector('.text-center.py-8');
                    if (toNoTasks) {
                        toNoTasks.style.display = toTasks.length === 0 ? 'block' : 'none';
                    }
                }

                fetch('/task/personal/api/update-position/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                        'X-Requested-With': 'XMLHttpRequest'
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
                    
                    // Revert "No tasks" message visibility on error
                    if (fromColumnBody) {
                        var fromTasksAfterError = fromColumnBody.querySelectorAll('.personal-task');
                        var fromNoTasksAfterError = fromColumnBody.querySelector('.text-center.py-8');
                        if (fromNoTasksAfterError) {
                            fromNoTasksAfterError.style.display = fromTasksAfterError.length === 0 ? 'block' : 'none';
                        }
                    }
                    if (toColumnBody) {
                        var toTasksAfterError = toColumnBody.querySelectorAll('.personal-task');
                        var toNoTasksAfterError = toColumnBody.querySelector('.text-center.py-8');
                        if (toNoTasksAfterError) {
                            toNoTasksAfterError.style.display = toTasksAfterError.length === 0 ? 'block' : 'none';
                        }
                    }
                });
            }
        });
    });

    // Column reordering
    var kanbanContainer = document.getElementById('personalKanban');
    if (kanbanContainer) {
        new Sortable(kanbanContainer, {
            animation: 150,
            handle: '.column-header',
            ghostClass: 'sortable-ghost',
            onEnd: function(evt) {
                var columnIds = [];
                document.querySelectorAll('[data-column-id]').forEach(function(col) {
                    columnIds.push({
                        id: parseInt(col.getAttribute('data-column-id')),
                        order: parseInt(col.getAttribute('data-column-order') || 0)
                    });
                });

                // Update order based on new positions
                var items = kanbanContainer.querySelectorAll('[data-column-id]');
                items.forEach(function(item, index) {
                    var colId = item.getAttribute('data-column-id');
                    var orderInput = item.querySelector('.column-order-input');
                    if (orderInput) orderInput.value = index;
                });

                fetch('/task/personal/api/update-column-position/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({
                        positions: Array.from(items).map(function(item, index) {
                            return { id: parseInt(item.getAttribute('data-column-id')), order: index };
                        })
                    })
                })
                .then(function(r) { return r.json(); })
                .catch(function(err) {
                    console.error('Failed to update column order:', err);
                    showToast('Failed to update column order', 'error');
                });
            }
        });
    }
});
