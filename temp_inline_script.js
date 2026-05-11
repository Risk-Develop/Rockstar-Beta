
       function personalBoardsData() {
            return {
                scrolled: false,
                archivedDrawerOpen: false,
                archivedBoards: [],           // Full list from API
                selectedArchivedBoardIds: [], // Selected for bulk ops
                archivedFilterName: '',
                archivedFilterDateFrom: '',
                archivedFilterDateTo: '',
                 autoPurgeDays: 30,
                 isPurging: false,
                 previewBoard: null,
                 previewTasks: [],
                 showPreview: false,
                confirmModalOpen: false,
                confirmModalConfig: {
                    title: '',
                    message: '',
                    type: 'danger',
                    confirmText: 'Confirm',
                    iconBgClass: 'bg-red-500/20',
                    iconClass: 'fa-exclamation-triangle text-red-500',
                    buttonClass: 'bg-red-600 hover:bg-red-500 text-white focus:ring-red-500',
                    buttonIconClass: 'fa-trash-alt'
                },
                confirmModalCallback: null,
                expanded: false,
                mobileStatsOpen: {},
                quickAddOpen: null,
                createModalOpen: false,
                selectedTemplate: null,
                createFormName: '',
                createFormDesc: '',
                // Reorder mode
                reorderMode: false,
                focusedBoardIndex: 0,

                 // Predefined board templates
                 boardTemplates: [
                     {
                         id: 'goals',
                         name: 'Goals',
                         description: 'Track your long-term and short-term goals with milestones and progress tracking.',
                         tag: 'work',
                         icon: 'fas fa-bullseye',
                         color: '#3b82f6',
                         columnCount: 5
                     },
                     {
                         id: 'habits',
                         name: 'Habits',
                         description: 'Build daily habits and track your consistency over time.',
                         tag: 'personal',
                         icon: 'fas fa-repeat',
                         color: '#8b5cf6',
                         columnCount: 4
                     },
                     {
                         id: 'backlog',
                         name: 'Backlog',
                         description: 'Capture ideas, tasks, and things to process later without losing them.',
                         tag: 'work',
                         icon: 'fas fa-inbox',
                         color: '#6b7280',
                         columnCount: 3
                     },
                     {
                         id: 'daily',
                         name: 'Daily Tasks',
                         description: 'Manage your daily to-do list with urgent, normal, and low priority tasks.',
                         tag: 'personal',
                         icon: 'fas fa-calendar-day',
                         color: '#10b981',
                         columnCount: 4
                     },
                     {
                         id: 'learning',
                         name: 'Learning',
                         description: 'Track courses to take, books to read, and skills to develop.',
                         tag: 'learning',
                         icon: 'fas fa-graduation-cap',
                         color: '#ec4899',
                         columnCount: 5
                     },
                     {
                         id: 'health',
                         name: 'Health & Fitness',
                         description: 'Monitor workouts, nutrition, and health metrics in one place.',
                         tag: 'health',
                         icon: 'fas fa-heartbeat',
                         color: '#10b981',
                         columnCount: 4
                     },
                     {
                         id: 'finance',
                         name: 'Finance',
                         description: 'Track budgets, bills, savings goals, and investments.',
                         tag: 'finance',
                         icon: 'fas fa-chart-line',
                         color: '#f59e0b',
                         columnCount: 5
                     },
                     {
                         id: 'home',
                         name: 'Home Projects',
                         description: 'Manage home improvement tasks, repairs, and family activities.',
                         tag: 'home',
                         icon: 'fas fa-home',
                         color: '#f97316',
                         columnCount: 5
                     },
                     {
                         id: 'hobby',
                         name: 'Hobbies',
                         description: 'Organize your hobby projects, creative work, and fun activities.',
                         tag: 'hobby',
                         icon: 'fas fa-gamepad',
                         color: '#06b6d4',
                         columnCount: 4
                     }
                 ],

                 // Stats data from Django template
                statsData: {
                    boards: 0,
                    boardsLastWeek: 0,
                    tasks: 0,
                    tasksLastWeek: 0,
                    completed: 0,
                    completedLastWeek: 0,
                    productivity: 0,
                    sparkBoards: [0],
                    sparkTasks: [0],
                    sparkCompleted: [0]
                },

            init() {
            const handler = () => { this.scrolled = window.scrollY > 300; };
            window.addEventListener('scroll', handler, { passive: true });
            this.$cleanup = () => window.removeEventListener('scroll', handler);

             // Initialize Sortable for drag-and-drop reordering
             const grid = document.querySelector('#boards-grid');
             if (grid && typeof Sortable !== 'undefined') {
                 new Sortable(grid, {
                     handle: '.drag-handle',
                     animation: 150,
                     ghostClass: 'sortable-ghost',
                     dragClass: 'sortable-drag',
                     easing: 'cubic-bezier(1, 0, 0, 1)',
                     onEnd: (evt) => {
                         this.updateBoardOrder();
                     }
                 });
             }

            // Event delegation for archived drawer buttons
            const archivedContainer = document.getElementById('archived-boards-container');
            if (archivedContainer) {
                archivedContainer.addEventListener('click', (e) => {
                    const restoreBtn = e.target.closest('.restore-btn');
                    if (restoreBtn) {
                        const card = restoreBtn.closest('[data-board-id]');
                        const boardId = card.dataset.boardId;
                        this.restoreBoard(boardId);
                    }
                    const deleteBtn = e.target.closest('.delete-btn');
                    if (deleteBtn) {
                        const card = deleteBtn.closest('[data-board-id]');
                        const boardId = card.dataset.boardId;
                        const boardName = card.dataset.boardName;
                        this.deleteBoard(boardId, boardName);
                    }
                });

                // Event delegation for checkboxes
                archivedContainer.addEventListener('change', (e) => {
                    if (e.target.classList.contains('archived-board-checkbox')) {
                        const boardId = parseInt(e.target.value);
                        this.toggleBoardSelection(boardId);
                    }
                });
            }

            // Select all checkbox handler
            const selectAll = document.getElementById('select-all-archived');
            if (selectAll) {
                selectAll.addEventListener('change', (e) => {
                    this.toggleSelectAll();
                });
            }

            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                // Ignore if user is typing in an input/textarea/select
                const tag = e.target.tagName.toLowerCase();
                if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable) {
                    return;
                }

                 // Reorder mode shortcuts (priority)
                  if (this.reorderMode) {
                      if (e.key === 'Escape') {
                          e.preventDefault();
                          this.toggleReorderMode();
                          return;
                      }
                      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                          e.preventDefault();
                          const active = document.activeElement;
                          const boardEl = active.closest('.relative[data-board-id]');
                          if (boardEl) {
                              const dir = e.key === 'ArrowDown' ? 1 : -1;
                              this.moveBoard(boardEl, dir);
                          }
                      }
                      if (e.key === 'Enter') {
                          e.preventDefault();
                          const active = document.activeElement;
                          const boardEl = active.closest('.relative[data-board-id]');
                          if (boardEl) {
                              this.moveBoard(boardEl, 1);
                          }
                      }
                      return;
                  }

                // N — Create board
                if ((e.key === 'n' || e.key === 'N') && !e.ctrlKey && !e.metaKey) {
                    e.preventDefault();
                    if (!this.createModalOpen) {
                        this.openCreateModal();
                    } else {
                        const nameInput = document.getElementById('create_board_name_input');
                        if (nameInput) nameInput.focus();
                    }
                }
                // Ctrl/Cmd+B — also create board
                if (e.ctrlKey || e.metaKey) {
                    if (e.key === 'b' || e.key === 'B') {
                        e.preventDefault();
                        if (!this.createModalOpen) {
                            this.openCreateModal();
                        } else {
                            const nameInput = document.getElementById('create_board_name_input');
                            if (nameInput) nameInput.focus();
                        }
                    }
                }
                // R — Toggle reorder mode
                if ((e.key === 'r' || e.key === 'R') && !e.ctrlKey && !e.metaKey) {
                    e.preventDefault();
                    this.toggleReorderMode();
                }
                // A — Open archived drawer
                if ((e.key === 'a' || e.key === 'A') && !e.ctrlKey && !e.metaKey) {
                    e.preventDefault();
                    this.openArchivedDrawer();
                }
                  // Esc — Close any open modal/drawer
                  if (e.key === 'Escape') {
                      e.preventDefault();
                      if (this.createModalOpen) this.closeCreateModal();
                      if (this.archivedDrawerOpen) this.closeArchivedDrawer();
                      if (this.confirmModalOpen) this.closeConfirmModal();
                      if (this.showPreview) this.closePreview();
                      // Close edit modal (global function)
                      if (typeof closeEditModal === 'function') closeEditModal();
                      // Close help modal if open
                      const helpModal = document.getElementById('helpModal');
                      if (helpModal && helpModal.style.display === 'flex') {
                          helpModal.style.display = 'none';
                      }
                  }
            });

            // Initialize micro-interactions
            this.initRippleEffect();
            this.initMagneticDragHandle();
            this.initCardFlip();
            this.initTaskPreview();

             // Store reference globally
             window.PersonalBoardsData = this;
         },

          // ========== Stats Dashboard Computed ==========
          get statsTotalBoards() { return this.statsData.boards; },
          get statsTotalTasks() { return this.statsData.tasks; },
          get statsCompletedTasks() { return this.statsData.completed; },
          get statsAvgTasks() {
              return this.statsData.boards > 0 ? Math.round(this.statsData.tasks / this.statsData.boards * 10) / 10 : 0;
          },
          get statsProductivityScore() { return this.statsData.productivity; },

          // ========== Archive Management Computed ==========
          get filteredArchivedBoards() {
              return this.archivedBoards.filter(board => {
                  // Name filter
                  if (this.archivedFilterName && !board.name.toLowerCase().includes(this.archivedFilterName.toLowerCase())) {
                      return false;
                  }
                  // Date from filter
                  if (this.archivedFilterDateFrom && board.archived_at) {
                      const boardDate = new Date(board.archived_at).toISOString().split('T')[0];
                      if (boardDate < this.archivedFilterDateFrom) return false;
                  }
                  // Date to filter
                  if (this.archivedFilterDateTo && board.archived_at) {
                      const boardDate = new Date(board.archived_at).toISOString().split('T')[0];
                      if (boardDate > this.archivedFilterDateTo) return false;
                  }
                  return true;
              });
          },

          areAllFilteredSelected() {
              if (this.filteredArchivedBoards.length === 0) return false;
              return this.filteredArchivedBoards.every(board => this.selectedArchivedBoardIds.includes(board.id));
          },

         getTrendData(type) {
             const current = this.statsData[type];
             const previous = this.statsData[type + 'LastWeek'];
             if (previous === 0) return { percent: 0, direction: 'neutral' };
             const diff = current - previous;
             const percent = Math.round((diff / previous) * 100);
             return { percent, direction: percent > 0 ? 'up' : percent < 0 ? 'down' : 'neutral' };
         },

         getTrendClass(type) {
             const { direction } = this.getTrendData(type);
             return direction === 'up' ? 'up' : direction === 'down' ? 'down' : 'neutral';
         },

         getTrendArrow(type) {
             const { direction } = this.getTrendData(type);
             return direction === 'up' ? 'fa-arrow-up' : direction === 'down' ? 'fa-arrow-down' : 'fa-minus';
         },

         getTrendPercent(type) {
             const { percent } = this.getTrendData(type);
             return Math.abs(percent);
         },

          // Sparkline scales and paths
          getScaledPath(data, width = 50, height = 20) {
              if (!data || data.length < 2) return '';
              const min = Math.min(...data);
              const max = Math.max(...data);
              const range = max - min || 1;
              const stepX = width / (data.length - 1);
              const points = data.map((val, i) => {
                  const x = i * stepX;
                  const y = height - ((val - min) / range) * height;
                  return `${x.toFixed(1)},${y.toFixed(1)}`;
              });
              return points.join(' ');
          },

          getAreaPath(data, width = 50, height = 20) {
              if (!data || data.length < 2) return '';
              const min = Math.min(...data);
              const max = Math.max(...data);
              const range = max - min || 1;
              const stepX = width / (data.length - 1);
              const points = [`0,${height}`]; // start bottom-left
              data.forEach((val, i) => {
                  const x = i * stepX;
                  const y = height - ((val - min) / range) * height;
                  points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
              });
              points.push(`${width},${height}`); // bottom-right
              return points.join(' ');
          },

          // ========== MICRO-INTERACTIONS ==========
              initRippleEffect() {
                  const selectors = ['button', '.create-btn', '.stat-item', '.stat-badge', '.quick-link', '.card-actions button', '[onclick*="openEditModal"]', '[onclick*="confirmArchive"]', '.quick-add-toggle', '.quick-add-form button[type="submit"]'];
                 const elements = new Set();
                 selectors.forEach(sel => { document.querySelectorAll(sel).forEach(el => elements.add(el)); });
                 elements.forEach(el => {
                     if (el.dataset.rippleBound === 'true') return; // Skip already initialized
                     if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
                     el.classList.add('ripple');
                     el.addEventListener('click', function(e) {
                         if (this.classList.contains('animate')) return;
                         if (this.disabled) return;
                         const rect = this.getBoundingClientRect();
                         const x = e.clientX - rect.left;
                         const y = e.clientY - rect.top;
                         const ripple = document.createElement('span');
                         ripple.style.cssText = `position: absolute; left: ${x}px; top: ${y}px; width: 0; height: 0; background: rgba(255,255,255,0.4); border-radius: 50%; transform: translate(-50%,-50%); pointer-events: none; z-index: 0;`;
                         this.classList.add('animate');
                         this.appendChild(ripple);
                         ripple.animate([{ width: '0px', height: '0px', opacity: 0.6 }, { width: '400px', height: '400px', opacity: 0 }], { duration: 600, easing: 'ease-out' });
                         setTimeout(() => { ripple.remove(); this.classList.remove('animate'); }, 600);
                     });
                     el.dataset.rippleBound = 'true';
                 });
             },

             initMagneticDragHandle() {
                 const handles = document.querySelectorAll('.drag-handle');
                 handles.forEach(handle => {
                     if (handle.dataset.magneticBound === 'true') return;
                     handle.addEventListener('mousemove', (e) => {
                         const rect = handle.getBoundingClientRect();
                         const centerX = rect.left + rect.width/2;
                         const centerY = rect.top + rect.height/2;
                         const deltaX = (e.clientX - centerX) * 0.25;
                         const deltaY = (e.clientY - centerY) * 0.25;
                         handle.classList.add('magnetic-active');
                         handle.style.transform = `translate(${deltaX}px, ${deltaY}px) scale(1.25)`;
                     });
                     handle.addEventListener('mouseleave', () => {
                         handle.classList.remove('magnetic-active');
                         handle.style.transform = '';
                     });
                     handle.dataset.magneticBound = 'true';
                 });
             },

            initCardFlip() {
                const originalOpen = window.openEditModal;
                window.openEditModal = function(boardId, name, description) {
                    const card = document.querySelector(`[data-board-id="${boardId}"]`);
                    if (card) {
                        card.classList.add('flip-animate');
                        setTimeout(() => {
                            originalOpen(boardId, name, description);
                            setTimeout(() => card.classList.remove('flip-animate'), 500);
                        }, 250);
                    } else {
                        originalOpen(boardId, name, description);
                    }
                };
            },

             initTaskPreview() {
                 const cards = document.querySelectorAll('[data-board-id]');
                 cards.forEach(card => {
                     if (card.querySelector('.task-preview-tooltip')) return; // Already initialized
                     const boardId = card.dataset.boardId;
                     const trigger = card.querySelector('.board-card');
                     if (!trigger) return;
                    const tooltip = document.createElement('div');
                    tooltip.className = 'task-preview-tooltip absolute ml-2 z-30 w-72 bg-white dark:bg-gray-800 rounded-xl shadow-2xl right-3 border border-gray-200 dark:border-gray-700 overflow-hidden';
                    tooltip.innerHTML = `
                        <div class="p-4 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                            <div class="flex items-center justify-between">
                                <h4 class="text-sm font-semibold text-gray-800 dark:text-gray-200">Tasks</h4>
                                <span class="text-xs text-gray-500 dark:text-gray-400">Loading...</span>
                            </div>
                        </div>
                        <div class="mini-kanban-column p-2 space-y-1"><div class="text-center text-gray-400 text-xs py-4">Loading tasks...</div></div>
                    `;
                    card.appendChild(tooltip);
                    let fetched = false;
                    const show = () => tooltip.classList.add('show');
                    const hide = () => tooltip.classList.remove('show');

                    trigger.addEventListener('mouseenter', async () => {
                        if (fetched && tooltip.classList.contains('show')) return;
                        if (!fetched) {
                            try {
                                const previewUrl = card.dataset.previewUrl;
                                if (!previewUrl) { fetched = true; return; }
                                const response = await fetch(previewUrl);
                                const data = await response.json();
                                if (data.tasks && data.tasks.length > 0) {
                                    const colorMap = { 'urgent': '#dc2626', 'high': '#ef4444', 'medium': '#eab308', 'low': '#3b82f6' };
                                     tooltip.innerHTML = `
                                      <div class="p-4 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                                          <div class="flex items-center justify-between">
                                              <h4 class="text-sm font-semibold text-gray-800 dark:text-gray-200">Tasks</h4>
                                              <span class="text-xs text-gray-500 dark:text-gray-400">${data.tasks.length} total</span>
                                          </div>
                                      </div>
                                      <div class="mini-kanban-column p-2 space-y-1 max-h-48 overflow-y-auto">

                                             ${data.tasks.map(task => {
                                                 const color = colorMap[task.priority] || '#6b7280';
                                                 const priorityLabel = task.priority.charAt(0).toUpperCase();
                                                 const dueDate = task.deadline ? new Date(task.deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : null;
                                                 return `<div class="mini-task-item flex items-center gap-2 px-2 py-1.5 rounded text-sm ${task.is_completed ? 'completed' : 'text-gray-700 dark:text-gray-200'}" style="border-left: 3px solid ${color}">
                                                     <input type="checkbox" ${task.is_completed ? 'checked' : ''} disabled class="w-3.5 h-3.5 accent-green-500">
                                                     <span class="flex-1 truncate">${this.escapeHtml(task.title)}</span>
                                                     ${dueDate ? `<span class="flex-shrink-0 px-1.5 py-0.5 rounded text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700">${dueDate}</span>` : ''}
                                                     <span class="flex-shrink-0 px-1.5 py-0.5 rounded text-xs font-medium text-white" style="background-color: ${color}">${priorityLabel}</span>
                                                 </div>`;
                                             }).join('')}
                                         </div>
                                  <div class="p-2 border-t border-gray-100 dark:border-gray-700 text-center bg-gray-50 dark:bg-gray-900">
                                      <a href="${card.dataset.detailUrl}" class="text-xs text-blue-600 dark:text-blue-400 hover:underline">Open Board →</a>
                                  </div>
                                     `;
                                } else {
                                    tooltip.innerHTML = `<div class="p-4 text-center text-gray-500 dark:text-gray-400 text-sm">No tasks yet</div>`;
                                }
                                fetched = true;
                            } catch (err) {
                                console.error('Error fetching tasks preview:', err);
                                tooltip.innerHTML = `<div class="p-4 text-center text-red-500 text-sm">Failed to load</div>`;
                            }
                        }
                        show();
                    });

                    trigger.addEventListener('mouseleave', () => {
                        setTimeout(() => { if (!tooltip.matches(':hover')) hide(); }, 100);
                    });

                    tooltip.addEventListener('mouseenter', show);
                    tooltip.addEventListener('mouseleave', hide);
                    trigger.addEventListener('focus', show);
                    trigger.addEventListener('blur', hide);
                });
            },

            boardColors: [
                '#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444',
                '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1'
            ],

            getBoardBorderColor(tag) {
                 const colorMap = {
                     'work': '#3b82f6',
                     'personal': '#8b5cf6',
                     'health': '#10b981',
                     'finance': '#f59e0b',
                     'learning': '#ec4899',
                     'home': '#f97316',
                     'hobby': '#06b6d4'
                 };
                 return colorMap[tag] || '#9ca3af';
            },

              adjustColor(hex, percent) {
                  const num = parseInt(hex.replace('#', ''), 16),
                        amt = Math.round(2.55 * percent),
                        R = (num >> 16) + amt,
                        G = (num >> 8 & 0x00FF) + amt,
                        B = (num & 0x0000FF) + amt;
                  return '#' + (0x1000000 +
                      (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
                      (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
                      (B < 255 ? B < 1 ? 0 : B : 255)
                  ).toString(16).slice(1);
              },

               // Reorder mode
               toggleReorderMode() {
                   this.reorderMode = !this.reorderMode;
                   const grid = document.querySelector('#boards-grid');
                   const cards = grid ? grid.querySelectorAll('.relative[data-board-id]') : [];

                  if (this.reorderMode) {
                      // Make cards focusable, add visual indicator
                      cards.forEach(card => card.setAttribute('tabindex', '0'));
                      if (cards.length) cards[0].focus();
                      if (grid) grid.classList.add('reorder-mode');
                  } else {
                      cards.forEach(card => card.setAttribute('tabindex', '-1'));
                      if (grid) grid.classList.remove('reorder-mode');
                  }
              },

              moveBoard(boardEl, direction) {
                  const grid = boardEl.parentNode;
                  if (direction === 1) {
                      // Move down: swap with next sibling
                      const next = boardEl.nextElementSibling;
                      if (next) grid.insertBefore(next, boardEl);
                  } else {
                      // Move up: swap with previous sibling
                      const prev = boardEl.previousElementSibling;
                      if (prev) grid.insertBefore(boardEl, prev);
                  }
                  // Persist new order
                  this.updateBoardOrder();
                  // Keep focus on moved board
                  boardEl.focus();
              },

            // Create Board Modal methods
            openCreateModal() {
                // Close help modal if open
                const helpModal = document.getElementById('helpModal');
                if (helpModal && helpModal.style.display === 'flex') {
                    helpModal.style.display = 'none';
                }
                this.createModalOpen = true;
                this.selectedTemplate = null;
                this.createFormName = '';
                this.createFormDesc = '';
            },

            closeCreateModal() {
                this.createModalOpen = false;
            },

            selectTemplate(template) {
                this.selectedTemplate = template;
                this.createFormName = template.name;
                this.createFormDesc = template.description || '';
            },

            clearSelection() {
                this.selectedTemplate = null;
                this.createFormName = '';
                this.createFormDesc = '';
            },

            getTagBadgeClass(tag) {
                const classes = {
                    'work': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
                    'personal': 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
                    'health': 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
                    'finance': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
                    'learning': 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300',
                    'home': 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
                    'hobby': 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300'
                };
                return classes[tag] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
            },

            getTagLabel(tag) {
                const labels = {
                    'work': 'Work',
                    'personal': 'Personal',
                    'health': 'Health',
                    'finance': 'Finance',
                    'learning': 'Learning',
                    'home': 'Home',
                    'hobby': 'Hobby'
                };
                return labels[tag] || 'Other';
            },

            getTagColor(tag) {
                const colors = {
                    'work': '#3b82f6',
                    'personal': '#8b5cf6',
                    'health': '#10b981',
                    'finance': '#f59e0b',
                    'learning': '#ec4899',
                    'home': '#f97316',
                    'hobby': '#06b6d4'
                };
                return colors[tag] || '#9ca3af';
            },

            getTagIcon(tag) {
                const icons = {
                    'work': 'fas fa-briefcase',
                    'personal': 'fas fa-user',
                    'health': 'fas fa-heartbeat',
                    'finance': 'fas fa-chart-line',
                    'learning': 'fas fa-graduation-cap',
                    'home': 'fas fa-home',
                    'hobby': 'fas fa-gamepad'
                };
                return icons[tag] || 'fas fa-clipboard';
            },

             // Duplicate board
             async duplicateBoard(boardId, boardName) {
                 this.openConfirmModal({
                     title: 'Duplicate Board',
                     message: `Create an exact copy of "${boardName}"? All tasks, columns, and settings will be duplicated.`,
                     type: 'info',
                     confirmText: 'Duplicate',
                     iconBgClass: 'bg-blue-500/20',
                     iconClass: 'fa-copy text-blue-500',
                     buttonClass: 'bg-blue-600 hover:bg-blue-500 text-white focus:ring-blue-500',
                     buttonIconClass: 'fa-copy'
                 }, async () => {
                     try {
                         const response = await fetch(
                             `0`.replace('0', boardId),
                             {
                                 method: 'POST',
                                 headers: {
                                     'X-CSRFToken': this.getCsrfToken(),
                                     'X-Requested-With': 'XMLHttpRequest'
                                 }
                             }
                         );
                          const data = await response.json();
                           if (data.success) {
                               // Add new board to grid without page reload
                               const board = data.board;
                               const grid = document.querySelector('#boards-grid');
                               if (grid) {
                                  let cardHtml;
                                  try {
                                      cardHtml = buildBoardCard(board);
                                  } catch (err) {
                                      console.error('buildBoardCard error:', err);
                                      // Fallback: reload page
                                      window.location.reload();
                                      return;
                                  }
                                  const tempDiv = document.createElement('div');
                                  tempDiv.innerHTML = cardHtml;
                                  const newCard = tempDiv.firstElementChild;
                                  grid.insertBefore(newCard, grid.firstChild);

                                  // Initialize Alpine bindings for dynamic card
                                  if (window.Alpine && typeof window.Alpine.initTree === 'function') {
                                      window.Alpine.initTree(newCard);
                                  }

                                  // Initialize micro-interactions for new card
                                  window.PersonalBoardsData.initRippleEffect();
                                  window.PersonalBoardsData.initMagneticDragHandle();
                                  window.PersonalBoardsData.initTaskPreview();

                                   // Update board count stat
                                   window.PersonalBoardsData.statsData.boards++;
                                   // Update tasks and completed stats
                                   window.PersonalBoardsData.statsData.tasks += board.total_tasks || 0;
                                   window.PersonalBoardsData.statsData.completed += board.completed_tasks || 0;
                                   window.PersonalBoardsData.statsData.productivity = window.PersonalBoardsData.statsData.tasks > 0
                                       ? Math.round(window.PersonalBoardsData.statsData.completed / window.PersonalBoardsData.statsData.tasks * 100)
                                       : 0;

                                   showToast('Board duplicated!', 'success');
                               } else {
                                  // No grid (shouldn't happen), reload as fallback
                                  window.location.reload();
                              }
                          } else {
                              alert('Error: ' + (data.error || 'Failed to duplicate board'));
                          }
                     } catch (err) {
                         console.error('Error:', err);
                         alert('An error occurred while duplicating the board.');
                     }
                 });
             },

            async openArchivedDrawer() {
                this.archivedDrawerOpen = true;
                this.selectedArchivedBoardIds = [];
                this.archivedFilterName = '';
                this.archivedFilterDateFrom = '';
                this.archivedFilterDateTo = '';
                await this.fetchArchivedBoards();
            },

            closeArchivedDrawer() {
                this.archivedDrawerOpen = false;
            },

            async applyArchivedFilters() {
                await this.fetchArchivedBoards();
            },

            clearArchivedFilters() {
                this.archivedFilterName = '';
                this.archivedFilterDateFrom = '';
                this.archivedFilterDateTo = '';
                this.fetchArchivedBoards();
            },

            async fetchArchivedBoards() {
                const container = document.getElementById('archived-boards-container');
                try {
                    const params = new URLSearchParams();
                    if (this.archivedFilterName) params.append('search', this.archivedFilterName);
                    if (this.archivedFilterDateFrom) params.append('date_from', this.archivedFilterDateFrom);
                    if (this.archivedFilterDateTo) params.append('date_to', this.archivedFilterDateTo);
                    const url = `0?${params.toString()}`;

                    const response = await fetch(url);
                    const data = await response.json();

                    if (data.boards && data.boards.length > 0) {
                        this.archivedBoards = data.boards;
                        this.renderArchivedBoards();
                    } else {
                        this.archivedBoards = [];
                        container.innerHTML = `
                            <div class="text-center py-12">
                                <div class="mx-auto w-12 h-12 mb-4 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                                    <i class="fas fa-archive text-gray-400"></i>
                                </div>
                                <p class="text-gray-500 dark:text-gray-400">No archived boards match your filters</p>
                            </div>
                        `;
                    }
                } catch (error) {
                    console.error('Error fetching archived boards:', error);
                    container.innerHTML = `
                        <div class="text-center py-12">
                            <p class="text-red-500 dark:text-red-400">Failed to load archived boards</p>
                            <button @click="fetchArchivedBoards()"
                                    class="mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                                Retry
                            </button>
                        </div>
                    `;
                }
            },

            renderArchivedBoards() {
                const container = document.getElementById('archived-boards-container');
                if (!container) return;

                if (this.filteredArchivedBoards.length === 0) {
                    container.innerHTML = `
                        <div class="text-center py-12">
                            <div class="mx-auto w-12 h-12 mb-4 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                                <i class="fas fa-filter text-gray-400"></i>
                            </div>
                            <p class="text-gray-500 dark:text-gray-400">No boards match current filters</p>
                        </div>
                    `;
                    // Update select all checkbox state
                    const selectAll = document.getElementById('select-all-archived');
                    if (selectAll) selectAll.checked = false;
                    return;
                }

                container.innerHTML = this.filteredArchivedBoards.map((board) => {
                    const isChecked = this.selectedArchivedBoardIds.includes(board.id);
                    return `
                    <div class="bg-white dark:bg-gray-700 rounded-lg p-3 border border-gray-200 dark:border-gray-600 shadow-sm hover:shadow-md transition-all"
                         data-board-id="${board.id}"
                         data-board-name="${this.escapeHtml(board.name)}"
                         data-board-description="${this.escapeHtml(board.description || '')}"
                         data-board-total-tasks="${board.total_tasks || 0}"
                         data-board-completed-tasks="${board.completed_tasks || 0}"
                         data-board-to-do-column-id="${board.to_do_column_id || ''}"
                         data-board-tag="${board.tag || ''}"
                         data-archived-at="${board.archived_at || ''}"
                         onclick="if (!event.target.closest('button, input')) { window.PersonalBoardsData.openPreview(${board.id}); }">
                        <div class="flex items-start gap-2">
                            <!-- Checkbox -->
                            <input type="checkbox"
                                   value="${board.id}"
                                   ${isChecked ? 'checked' : ''}
                                   onclick="event.stopPropagation()"
                                   class="archived-board-checkbox mt-1 w-4 h-4 text-blue-600 border-gray-300 dark:border-gray-500 rounded focus:ring-blue-500 cursor-pointer">
                            <div class="flex-1 min-w-0">
                                <div class="flex items-start justify-between mb-2">
                                    <div class="flex-1 min-w-0">
                                        <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate mb-1">
                                            ${this.escapeHtml(board.name)}
                                        </h3>
                                        <p class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
                                            ${board.description ? this.escapeHtml(board.description) : 'No description'}
                                        </p>
                                    </div>
                                    <span class="text-xs text-gray-500 dark:text-gray-400 ml-2 flex-shrink-0">
                                        ${board.total_tasks || 0} tasks
                                    </span>
                                </div>

                                <div class="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
                                    <div class="flex items-center gap-2">
                                        <span class="text-green-600 dark:text-green-400">
                                            <i class="fas fa-check-circle mr-1"></i>
                                            ${board.completed_tasks || 0} done
                                        </span>
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <button type="button"
                                                class="restore-btn px-2 py-1 rounded text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors"
                                                title="Restore board">
                                            <i class="fas fa-undo"></i> Restore
                                        </button>
                                        <button type="button"
                                                class="delete-btn px-2 py-1 rounded text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
                                                title="Delete permanently">
                                            <i class="fas fa-trash"></i> Delete
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                     </div>
                 `;
                }).join('');

                // Update select all checkbox state after render
                this.$nextTick(() => {
                    const selectAll = document.getElementById('select-all-archived');
                    if (selectAll) {
                        selectAll.checked = this.areAllFilteredSelected();
                        // Indeterminate state
                        const selectedCount = this.selectedArchivedBoardIds.filter(id => 
                            this.filteredArchivedBoards.some(b => b.id === id)
                        ).length;
                        if (selectedCount > 0 && selectedCount < this.filteredArchivedBoards.length) {
                            selectAll.indeterminate = true;
                        } else {
                            selectAll.indeterminate = false;
                        }
                    }
                });
            },

            toggleSelectAll() {
                const allIds = this.filteredArchivedBoards.map(b => b.id);
                const currentlyAllSelected = this.areAllFilteredSelected();
                if (currentlyAllSelected) {
                    // Deselect all in current filter view
                    this.selectedArchivedBoardIds = this.selectedArchivedBoardIds.filter(id => !allIds.includes(id));
                } else {
                    // Add all filtered (avoid duplicates)
                    allIds.forEach(id => {
                        if (!this.selectedArchivedBoardIds.includes(id)) {
                            this.selectedArchivedBoardIds.push(id);
                        }
                    });
                }
                this.syncCheckboxes();
                this.updateSelectAllState();
            },

            toggleBoardSelection(boardId) {
                const index = this.selectedArchivedBoardIds.indexOf(boardId);
                if (index > -1) {
                    this.selectedArchivedBoardIds.splice(index, 1);
                } else {
                    this.selectedArchivedBoardIds.push(boardId);
                }
                this.updateSelectAllState();
            },

            updateSelectAllState() {
                this.$nextTick(() => {
                    const selectAll = document.getElementById('select-all-archived');
                    if (selectAll) {
                        const filtered = this.filteredArchivedBoards;
                        if (filtered.length === 0) {
                            selectAll.checked = false;
                            selectAll.indeterminate = false;
                            return;
                        }
                        const selectedInFilter = filtered.filter(b => this.selectedArchivedBoardIds.includes(b.id)).length;
                        selectAll.checked = selectedInFilter === filtered.length;
                        selectAll.indeterminate = selectedInFilter > 0 && selectedInFilter < filtered.length;
                    }
                });
            },

            syncCheckboxes() {
                const container = document.getElementById('archived-boards-container');
                if (!container) return;
                container.querySelectorAll('.archived-board-checkbox').forEach(cb => {
                    cb.checked = this.selectedArchivedBoardIds.includes(parseInt(cb.value));
                });
            },

            clearSelection() {
                this.selectedArchivedBoardIds = [];
                this.syncCheckboxes();
                this.updateSelectAllState();
            },

            async bulkRestoreSelected() {
                if (this.selectedArchivedBoardIds.length === 0) return;

                const confirmed = confirm(`Restore ${this.selectedArchivedBoardIds.length} selected board(s)?`);
                if (!confirmed) return;

                try {
                    const response = await fetch("0", {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.getCsrfToken(),
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: JSON.stringify({ board_ids: this.selectedArchivedBoardIds })
                    });
                    const data = await response.json();
                    if (data.success) {
                        showToast(data.message || `Restored ${this.selectedArchivedBoardIds.length} board(s)`, 'success');
                        this.selectedArchivedBoardIds = [];
                        await this.fetchArchivedBoards();
                        // Reload page to show restored boards in main grid
                        setTimeout(() => location.reload(), 800);
                    } else {
                        alert('Error: ' + (data.error || 'Bulk restore failed'));
                    }
                } catch (err) {
                    console.error('Bulk restore error:', err);
                    alert('An error occurred during bulk restore.');
                }
            },

            async bulkDeleteSelected() {
                if (this.selectedArchivedBoardIds.length === 0) return;

                const confirmed = confirm(`Permanently delete ${this.selectedArchivedBoardIds.length} selected board(s)? This cannot be undone.`);
                if (!confirmed) return;

                try {
                    const response = await fetch("0", {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.getCsrfToken(),
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: JSON.stringify({ board_ids: this.selectedArchivedBoardIds })
                    });
                    const data = await response.json();
                    if (data.success) {
                        showToast(data.message || `Deleted ${this.selectedArchivedBoardIds.length} board(s)`, 'success');
                        this.selectedArchivedBoardIds = [];
                        await this.fetchArchivedBoards();
                    } else {
                        alert('Error: ' + (data.error || 'Bulk delete failed'));
                    }
                } catch (err) {
                    console.error('Bulk delete error:', err);
                    alert('An error occurred during bulk delete.');
                }
            },

            async autoPurge() {
                const days = parseInt(this.autoPurgeDays) || 30;
                const confirmed = confirm(`Purge all archived boards older than ${days} days? This cannot be undone.`);
                if (!confirmed) return;

                this.isPurging = true;
                try {
                    const response = await fetch("0", {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.getCsrfToken(),
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: JSON.stringify({ days: days })
                    });
                    const data = await response.json();
                    if (data.success) {
                        showToast(data.message || `Purged ${data.deleted_count || 0} old board(s)`, 'success');
                        await this.fetchArchivedBoards();
                    } else {
                        alert('Error: ' + (data.error || 'Auto-purge failed'));
                    }
                } catch (err) {
                    console.error('Auto-purge error:', err);
                    alert('An error occurred during auto-purge.');
                } finally {
                    this.isPurging = false;
                }
            },

            // Preview methods
            openPreview(boardId) {
                const board = this.archivedBoards.find(b => b.id === boardId);
                if (board) {
                    this.previewBoard = board;
                    this.previewTasks = []; // Clear previous tasks
                    this.showPreview = true;
                    this.fetchPreviewTasks(boardId);
                }
            },

            async fetchPreviewTasks(boardId) {
                try {
                    const url = "0".replace('0', boardId);
                    const response = await fetch(url);
                    const data = await response.json();
                    this.previewTasks = data.tasks || [];
                } catch (err) {
                    console.error('Error fetching preview tasks:', err);
                    this.previewTasks = [];
                }
            },

            closePreview() {
                this.showPreview = false;
                this.previewBoard = null;
            },

            // Preview actions
            restoreBoardFromPreview() {
                alert('Restore method invoked!');
                if (this.previewBoard) {
                    const boardId = this.previewBoard.id;
                    this.closePreview();
                    this.restoreBoard(boardId);
                }
            },

            deleteBoardFromPreview() {
                if (this.previewBoard) {
                    const boardId = this.previewBoard.id;
                    const boardName = this.previewBoard.name;
                    this.closePreview();
                    this.deleteBoard(boardId, boardName);
                }
            },

            // Helper methods
            getTagColor(tag) {
                const colorMap = {
                    'work': '#3b82f6',
                    'personal': '#8b5cf6',
                    'health': '#10b981',
                    'finance': '#f59e0b',
                    'learning': '#ec4899',
                    'home': '#f97316',
                    'hobby': '#06b6d4'
                };
                return colorMap[tag] || '#9ca3af';
            },

            getTagIcon(tag) {
                const iconMap = {
                    'work': 'fas fa-briefcase',
                    'personal': 'fas fa-user',
                    'health': 'fas fa-heartbeat',
                    'finance': 'fas fa-chart-line',
                    'learning': 'fas fa-graduation-cap',
                    'home': 'fas fa-home',
                    'hobby': 'fas fa-gamepad'
                };
                return iconMap[tag] || 'fas fa-clipboard';
            },

            getTagBadgeClass(tag) {
                const classMap = {
                    'work': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
                    'personal': 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
                    'health': 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
                    'finance': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
                    'learning': 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300',
                    'home': 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
                    'hobby': 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300'
                };
                return classMap[tag] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
            },

            getTagLabel(tag) {
                const labelMap = {
                    'work': 'Work',
                    'personal': 'Personal',
                    'health': 'Health',
                    'finance': 'Finance',
                    'learning': 'Learning',
                    'home': 'Home',
                    'hobby': 'Hobby'
                };
                return labelMap[tag] || 'Other';
            },

            getPriorityColor(priority) {
                const colorMap = {
                    'urgent': '#dc2626',
                    'high': '#ef4444',
                    'medium': '#eab308',
                    'low': '#3b82f6'
                };
                return colorMap[priority] || '#6b7280';
            },


            escapeHtml(unsafe) {
                return unsafe
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
            },

            escapeJs(unsafe) {
                if (unsafe == null) return '';
                return String(unsafe)
                    .replace(/\\/g, '\\\\')
                    .replace(/'/g, "\\'")
                    .replace(/"/g, '\\"')
                    .replace(/\n/g, '\\n')
                    .replace(/\r/g, '\\r')
                    .replace(/\u2028/g, '\\u2028')
                    .replace(/\u2029/g, '\\u2029');
            },

            // Persist board order after drag-and-drop
            async updateBoardOrder() {
                const grid = document.querySelector('#boards-grid');
                if (!grid) return;

                const cards = grid.querySelectorAll('.relative[data-board-id]');
                const orderedIds = Array.from(cards).map(card => card.dataset.boardId);

                try {
                    const response = await fetch("0", {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.getCsrfToken(),
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: JSON.stringify({ order: orderedIds })
                    });

                    const data = await response.json();
                    if (!data.success) {
                        console.error('Failed to update board order:', data.error);
                        showToast('Failed to save order', 'error');
                        // Optionally: reload to restore original order
                    }
                } catch (err) {
                    console.error('Error updating board order:', err);
                    showToast('Error saving order', 'error');
                }
            },

            // Confirm modal methods
            openConfirmModal(config, callback) {
                this.confirmModalConfig = { ...this.confirmModalConfig, ...config };
                this.confirmModalCallback = callback;
                this.confirmModalOpen = true;
                this.$nextTick(() => {
                    const modal = document.getElementById('confirmModal');
                    const actionBtn = document.getElementById('confirmModalActionBtn');
                    if (modal) modal.focus();
                    if (actionBtn) actionBtn.focus();
                });
            },

            closeConfirmModal() {
                this.confirmModalOpen = false;
                this.confirmModalCallback = null;
            },

            // Execute the callback (confirm action)
            executeConfirmCallback() {
                if (this.confirmModalCallback) {
                    this.confirmModalCallback();
                }
                this.closeConfirmModal();
            },

            // Helper: Get archive URL for a board
            getArchiveUrl(boardId) {
                const pattern = document.querySelector('[x-data="personalBoardsData()"]')?.dataset.archiveUrlPattern;
                if (pattern) {
                    return pattern.replace('0', boardId);
                }
                return `/task/personal/${boardId}/archive/`;
            },

            // Helper: Get CSRF token from cookie or DOM
            getCsrfToken() {
                const token = document.querySelector('[name=csrfmiddlewaretoken]');
                return token ? token.value : '';
            },

            // Restore board - uses custom modal
            restoreBoard(boardId) {
                // Convert boardId to integer (from dataset string)
                boardId = parseInt(boardId, 10);
                if (isNaN(boardId)) return;

                // Remove from selection if present
                const idx = this.selectedArchivedBoardIds.indexOf(boardId);
                if (idx > -1) this.selectedArchivedBoardIds.splice(idx, 1);

                // Find board data before operation
                const board = this.archivedBoards.find(b => b.id === boardId);
                if (!board) return;

                this.openConfirmModal({
                    title: 'Restore Board',
                    message: 'Are you sure you want to restore this board? It will be moved back to your main dashboard.',
                    type: 'info',
                    confirmText: 'Restore',
                    iconBgClass: 'bg-blue-500/20',
                    iconClass: 'fa-undo text-blue-500',
                    buttonClass: 'bg-blue-600 hover:bg-blue-500 text-white focus:ring-blue-500',
                    buttonIconClass: 'fa-undo'
                }, async () => {
                    try {
                        const response = await fetch(
                            `0`.replace('0', boardId),
                            {
                                method: 'POST',
                                headers: {
                                    'X-CSRFToken': this.getCsrfToken(),
                                    'X-Requested-With': 'XMLHttpRequest'
                                }
                            }
                        );
                         const data = await response.json();
                         if (data.success || data.restored) {
                             // Create a mock element with dataset attributes for addBoardToGrid
                             const mockEl = document.createElement('div');
                             mockEl.dataset.boardId = board.id;
                             mockEl.dataset.boardName = board.name;
                             mockEl.dataset.boardDescription = board.description || '';
                             mockEl.dataset.boardTotalTasks = board.total_tasks || 0;
                             mockEl.dataset.boardCompletedTasks = board.completed_tasks || 0;
                             mockEl.dataset.boardToDoColumnId = board.to_do_column_id || '';
                             mockEl.dataset.boardTag = board.tag || '';

                             // Add to main grid
                             this.addBoardToGrid(boardId, mockEl);

                             // Remove from local archived boards array and refresh drawer
                             this.archivedBoards = this.archivedBoards.filter(b => b.id !== boardId);
                             this.renderArchivedBoards();

                             showToast('Board restored successfully!', 'success');
                         } else {
                             alert('Error: ' + (data.error || 'Failed to restore board'));
                         }
                    } catch (err) {
                        console.error('Error:', err);
                        alert('An error occurred while restoring the board.');
                    }
                });
            },

            // Add restored board to main grid from data object
            addBoardToGridFromData(board) {
                // Find the main board grid
                const grid = document.querySelector('#boards-grid');
                if (!grid) {
                    // No grid yet - reload page
                    window.location.reload();
                    return;
                }

                const color = this.getBoardBorderColor(board.tag || '');
                const adjustedColor = this.adjustColor(color, 40);
                const escapedName = this.escapeHtml(board.name);
                const escapedDesc = board.description ? this.escapeHtml(board.description) : 'Personal productivity board';
                const escapedNameJs = this.escapeJs(board.name);
                const escapedDescJs = this.escapeJs(board.description || '');
                const detailUrl = "0".replace('0', board.id);
                const totalTasks = board.total_tasks || 0;
                const completedTasks = board.completed_tasks || 0;
                const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
                const dashArray = totalTasks > 0 ? `${progressPercent}, 100` : '0, 100';

                const card = document.createElement('div');
                card.className = 'relative flip-card';
                card.dataset.boardId = board.id;
                card.dataset.previewUrl = "0".replace('0', board.id);
                card.dataset.detailUrl = detailUrl;
                card.dataset.boardTag = board.tag || '';

                card.innerHTML = `
                    <a href="${detailUrl}" draggable="false" class="board-card block rounded-xl p-5 bg-white dark:bg-gray-800 border border-2 transition-all duration-300 group cursor-pointer"
                       :style="'border-color: ' + getBoardBorderColor('${board.tag || ''}')"
                       aria-label="Open ${escapedName} personal board">
                        <div class="absolute top-0 left-0 right-0 h-1 rounded-t-xl" style="background: linear-gradient(90deg, ${color} 0%, ${adjustedColor} 100%)"></div>
                        <div class="pt-4">
                            <div class="flex items-start mb-3">
                                <button draggable="false"
                                        @click.stop
                                        class="drag-handle flex items-center justify-center w-6 h-6 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 border border-gray-200 dark:border-gray-600 transition-all shadow-sm text-xs font-medium cursor-grab me-3 flex-shrink-0"
                                        title="Drag to reorder"
                                        aria-label="Drag to reorder ${escapedName}">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                                        <circle cx="12" cy="6" r="2"></circle>
                                        <circle cx="12" cy="12" r="2"></circle>
                                        <circle cx="12" cy="18" r="2"></circle>
                                    </svg>
                                </button>
                                <div class="flex-1 min-w-0">
                                    <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors cursor-pointer px-2 py-1 -mx-2 -my-1 rounded"
                                        data-board-id="${board.id}"
                                        data-field="name"
                                        contenteditable="false"
                                        title="Click to edit">${escapedName}</h3>
                                    <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2 px-2 py-1 -mx-2 -my-1 rounded"
                                        data-board-id="${board.id}"
                                        data-field="description"
                                        contenteditable="false"
                                        title="Click to edit">${escapedDesc}</p>
                                    ${board.tag ? `
                                    <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium mt-2
                                              ${this.getTagBadgeClass(board.tag)}">
                                        ${this.getTagLabel(board.tag)}
                                    </span>` : ''}
                                </div>
                            </div>

                            <div class="hidden md:flex items-center gap-4 pt-3 border-t border-gray-100 dark:border-gray-700">
                                <div class="flex items-center gap-1.5 text-gray-600 dark:text-gray-400">
                                    <i class="fas fa-tasks text-sm"></i>
                                    <span class="text-sm">${totalTasks}</span>
                                </div>
                                <div class="flex items-center gap-1.5 text-green-600 dark:text-green-400">
                                    <i class="fas fa-check-circle text-sm"></i>
                                    <span class="text-sm">${completedTasks}</span>
                                </div>
                                <div class="flex-1"></div>
                                <div class="flex items-center gap-2">
                                    <div class="relative w-8 h-8">
                                        <svg class="w-8 h-8" viewBox="0 0 36 36">
                                            <circle cx="18" cy="18" r="16"
                                                    fill="none"
                                                    stroke="currentColor"
                                                    stroke-width="3"
                                                    class="text-gray-200 dark:text-gray-700"></circle>
                                            <circle cx="18" cy="18" r="16"
                                                    fill="none"
                                                    stroke="currentColor"
                                                    stroke-width="3"
                                                    stroke-dasharray="${dashArray}"
                                                    class="text-emerald-500 progress-ring-circle"></circle>
                                        </svg>
                                    </div>
                                    <span class="text-xs font-medium text-gray-600 dark:text-gray-400">${progressPercent}%</span>
                                </div>
                             </div>
                        </div>
                    </a>
                    ${this.renderCardActions(boardId, escapedNameJs, escapedDescJs, boardTag, toDoColumnId)}
                `;

                // Insert card at the beginning of the grid
                grid.insertBefore(card, grid.firstChild);

                // Re-init ripple and magnetic for the new card's buttons
                this.initRippleEffect();
                this.initMagneticDragHandle();
            },

            // Render card action buttons for board card (shared)
            renderCardActions(boardId, escapedNameJs, escapedDescJs, boardTag, toDoColumnId) {
                return `
                <div class="card-actions absolute top-3 right-3 flex items-center gap-1.5">
                    <button @click.prevent="openQuickAdd(${boardId})"
                            class="quick-add-toggle flex items-center justify-center w-6 h-6 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-green-50 dark:hover:bg-green-900/40 text-gray-500 hover:text-green-600 dark:hover:text-green-400 border border-gray-200 dark:border-gray-600 hover:border-green-300 dark:hover:border-green-500 transition-all shadow-sm text-xs font-medium cursor-pointer"
                            title="Quick add task"
                            aria-label="Quick add task to ${escapedNameJs}">
                        <i class="fas fa-plus"></i>
                    </button>
                    <button onclick="event.stopPropagation(); openEditModal(${boardId}, '${escapedNameJs}', '${escapedDescJs}')"
                            class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-blue-50 dark:hover:bg-blue-900/40 text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500 transition-all shadow-sm text-xs font-medium cursor-pointer"
                            title="Edit board"
                            aria-label="Edit board ${escapedNameJs}">
                        <i class="fas fa-edit text-xs" aria-hidden="true"></i>
                        <span>Edit</span>
                    </button>
                    <form method="post" action="${this.getArchiveUrl(boardId)}" class="inline" onsubmit="return confirmArchive(event, '${escapedNameJs}')">
                        <input type="hidden" name="csrfmiddlewaretoken" value="${this.getCsrfToken()}">
                        <input type="hidden" name="column" value="${toDoColumnId}">
                        <button type="submit"
                                class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-red-50 dark:hover:bg-red-900/40 text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 border border-gray-200 dark:border-gray-600 hover:border-red-300 dark:hover:border-red-500 transition-all shadow-sm text-xs font-medium cursor-pointer"
                                title="Archive board"
                                aria-label="Archive board ${escapedNameJs}">
                            <i class="fas fa-archive text-xs" aria-hidden="true"></i>
                            <span>Archive</span>
                        </button>
                    </form>
                </div>
                `;
            },

            // Add restored board to main grid
            addBoardToGrid(boardId, sourceCard) {
                // Get board data from source card data attributes
                const name = sourceCard.dataset.boardName || '';
                const description = sourceCard.dataset.boardDescription || '';
                const totalTasks = parseInt(sourceCard.dataset.boardTotalTasks) || 0;
                const completedTasks = parseInt(sourceCard.dataset.boardCompletedTasks) || 0;
                const toDoColumnId = sourceCard.dataset.boardToDoColumnId || '';

                 // Find the main board grid
                 const grid = document.querySelector('#boards-grid');
                 if (!grid) {
                     console.warn('Board grid not found');
                     return;
                 }

                 // Get tag from source card (for border color)
                 const boardTag = sourceCard.dataset.boardTag || '';

                 // Compute colors for gradient
                 const color = this.getBoardBorderColor(boardTag);
                 const adjustedColor = this.adjustColor(color, 40);
                const card = document.createElement('div');
                card.className = 'relative flip-card';
                card.dataset.boardId = boardId;
                 card.dataset.previewUrl = "0".replace('0', boardId);
                 card.dataset.detailUrl = "0".replace('0', boardId);
                 card.dataset.boardTag = boardTag;

                const escapedName = this.escapeHtml(name);
                const escapedDesc = description ? this.escapeHtml(description) : 'Personal productivity board';
                const escapedNameJs = this.escapeJs(name);
                 const escapedDescJs = this.escapeJs(description);

                 const detailUrl = "0".replace('0', boardId);
                 const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
                const dashArray = totalTasks > 0 ? `${progressPercent}, 100` : '0, 100';

                  card.innerHTML = `
                      <a href="${detailUrl}" draggable="false" class="board-card block rounded-xl p-5 bg-white dark:bg-gray-800 border border-2 transition-all duration-300 group cursor-pointer"
                         :style="'border-color: ' + getBoardBorderColor('${boardTag}')"
                         aria-label="Open ${escapedName} personal board">
                       <div class="absolute top-0 left-0 right-0 h-1 rounded-t-xl" style="background: linear-gradient(90deg, ${color} 0%, ${adjustedColor} 100%)"></div>
                       <div class="pt-4">
                           <div class="flex items-start mb-3">
                               <!-- Drag handle - top-left inside card -->
                                <button draggable="false"
                                        @click.stop
                                        class="drag-handle flex items-center justify-center w-6 h-6 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 border border-gray-200 dark:border-gray-600 transition-all shadow-sm text-xs font-medium cursor-grab me-3 flex-shrink-0"
                                        title="Drag to reorder"
                                        aria-label="Drag to reorder ${escapedName}">
                                   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                                       <circle cx="12" cy="6" r="2"></circle>
                                       <circle cx="12" cy="12" r="2"></circle>
                                       <circle cx="12" cy="18" r="2"></circle>
                                   </svg>
                               </button>
                               <div class="flex-1 min-w-0">
                                   <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors cursor-pointer px-2 py-1 -mx-2 -my-1 rounded"
                                       data-board-id="${boardId}"
                                       data-field="name"
                                       contenteditable="false"
                                       title="Click to edit">${escapedName}</h3>
                                   <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2 px-2 py-1 -mx-2 -my-1 rounded"
                                      data-board-id="${boardId}"
                                      data-field="description"
                                      contenteditable="false"
                                      title="Click to edit">${escapedDesc}</p>
                               </div>
                           </div>
                           <div class="flex items-center gap-4 pt-3 border-t border-gray-100 dark:border-gray-700">
                               <div class="flex items-center gap-1.5 text-gray-600 dark:text-gray-400">
                                   <i class="fas fa-tasks text-sm"></i>
                                   <span class="text-sm">${totalTasks}</span>
                               </div>
                               <div class="flex items-center gap-1.5 text-green-600 dark:text-green-400">
                                   <i class="fas fa-check-circle text-sm"></i>
                                   <span class="text-sm">${completedTasks}</span>
                               </div>
                               <div class="flex-1"></div>
                               <!-- Priority indicators -->
                               <div class="flex items-center gap-2" data-priority-badges>
                                   0Populated by JS when counts change0
                               </div>
                               <!-- Progress ring -->
                               <div class="flex items-center gap-2">
                                   <div class="relative w-8 h-8">
                                       <svg class="w-8 h-8" viewBox="0 0 36 36">
                                           <circle cx="18" cy="18" r="16"
                                                   fill="none"
                                                   stroke="currentColor"
                                                   stroke-width="3"
                                                   class="text-gray-200 dark:text-gray-700"></circle>
                                           <circle cx="18" cy="18" r="16"
                                                   fill="none"
                                                   stroke="currentColor"
                                                   stroke-width="3"
                                                   stroke-dasharray="${dashArray}"
                                                   class="text-emerald-500 progress-ring-circle"></circle>
                                       </svg>
                                   </div>
                                   <span class="text-xs font-medium text-gray-600 dark:text-gray-400">${progressPercent}%</span>
                               </div>
                           </div>
                       </div>
                   </a>
                <div class="card-actions absolute top-3 right-3 flex items-center gap-1.5">
                        <button @click.prevent="openQuickAdd(${boardId})"
                                class="quick-add-toggle flex items-center justify-center w-6 h-6 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-green-50 dark:hover:bg-green-900/40 text-gray-500 hover:text-green-600 dark:hover:text-green-400 border border-gray-200 dark:border-gray-600 hover:border-green-300 dark:hover:border-green-500 transition-all shadow-sm text-xs font-medium cursor-pointer"
                                title="Quick add task"
                                aria-label="Quick add task to ${escapedName}">
                            <i class="fas fa-plus"></i>
                        </button>
                        <button onclick="event.stopPropagation(); openEditModal(${boardId}, '${escapedNameJs}', '${escapedDescJs}')"
                                class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-blue-50 dark:hover:bg-blue-900/40 text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500 transition-all shadow-sm text-xs font-medium cursor-pointer"
                                title="Edit board"
                                aria-label="Edit board ${escapedName}">
                            <i class="fas fa-edit text-xs" aria-hidden="true"></i>
                            <span>Edit</span>
                        </button>
                          <form method="post" action="${this.getArchiveUrl(boardId)}" class="inline" onsubmit="return confirmArchive(event, '${escapedNameJs}')">
                             <input type="hidden" name="csrfmiddlewaretoken" value="${this.getCsrfToken()}">
                             <button type="submit"
                                     class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-red-50 dark:hover:bg-red-900/40 text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 border border-gray-200 dark:border-gray-600 hover:border-red-300 dark:hover:border-red-500 transition-all shadow-sm text-xs font-medium cursor-pointer"
                                     title="Archive board"
                                     aria-label="Archive board ${escapedName}">
                                 <i class="fas fa-archive text-xs" aria-hidden="true"></i>
                                 <span>Archive</span>
                             </button>
                         </form>
                    </div>

                    {# Quick Add Task Inline Form (expands) #}
                     <div x-show="quickAddOpen === 0" x-transition class="absolute top-12 right-3 z-20 w-72 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 p-3"
                          @click.away="quickAddOpen = null">
                        <form @submit.prevent="submitQuickAdd(0)" class="space-y-2 quick-add-form">
                            0
                            <input type="text" name="title" placeholder="Task title" required
                                   class="w-full px-2.5 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500 quick-add-form-input">
                            <div class="flex gap-2">
                                <select name="priority" class="flex-1 px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500">
                                    <option value="low">Low</option>
                                    <option value="medium" selected>Medium</option>
                                    <option value="high">High</option>
                                    <option value="urgent">Urgent</option>
                                </select>
                                <input type="date" name="deadline"
                                   class="flex-1 px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500">
                            </div>
                            <input type="hidden" name="column" value="${toDoColumnId}">
                            <div class="flex justify-end gap-2">
                                <button type="button" @click="quickAddOpen = null"
                                        class="px-2.5 py-1.5 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200">Cancel</button>
                                <button type="submit"
                                        class="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors flex items-center gap-1">
                                    <i class="fas fa-plus text-[10px]"></i>Add
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
                  `;

                  // Prepend to grid (newest first)
                  grid.insertBefore(card, grid.firstChild);

                  // Initialize Alpine bindings for dynamic card
                  if (window.Alpine && typeof window.Alpine.initTree === 'function') {
                      window.Alpine.initTree(card);
                  }

                  // Initialize micro-interactions for the new card's elements
                  this.initRippleEffect();
                  this.initMagneticDragHandle();
                  this.initTaskPreview();

                  // Set form action dynamically using boardId
                  const newCardForm = card.querySelector('form');
                  if (newCardForm) {
                      newCardForm.action = this.getArchiveUrl(boardId);
                  }

                 // Update board count stat (reactive)
                 this.statsData.boards++;

                // Close drawer after a short delay
                setTimeout(() => {
                    this.closeArchivedDrawer();
                }, 300);
            },

            // Delete board permanently - uses custom modal
            deleteBoard(boardId, boardName) {
                // Convert boardId to integer (from dataset string)
                boardId = parseInt(boardId, 10);
                if (isNaN(boardId)) return;

                // Remove from selection if present
                const idx = this.selectedArchivedBoardIds.indexOf(boardId);
                if (idx > -1) this.selectedArchivedBoardIds.splice(idx, 1);

                this.openConfirmModal({
                    title: 'Delete Permanently',
                    message: `Are you sure you want to permanently delete "${boardName}"? This action cannot be undone and all associated tasks will be lost.`,
                    type: 'danger',
                    confirmText: 'Delete Forever',
                    iconBgClass: 'bg-red-500/20',
                    iconClass: 'fa-trash-alt text-red-500',
                    buttonClass: 'bg-red-600 hover:bg-red-500 text-white focus:ring-red-500',
                    buttonIconClass: 'fa-trash-alt'
                }, async () => {
                    try {
                        const response = await fetch(
                            `0`.replace('0', boardId),
                            {
                                method: 'POST',
                                headers: {
                                    'X-CSRFToken': this.getCsrfToken(),
                                    'X-Requested-With': 'XMLHttpRequest'
                                }
                            }
                        );
                        const data = await response.json();
                         if (data.deleted) {
                             const card = document.querySelector(`#archived-boards-container [data-board-id="${boardId}"]`);
                             if (card) {
                                 card.style.transition = 'opacity 0.3s';
                                 card.style.opacity = '0';
                                 setTimeout(() => card.remove(), 300);
                             }
                             showToast('Board deleted permanently!', 'success');
                         } else {
                            alert('Error: ' + (data.error || 'Failed to delete board'));
                        }
                    } catch (err) {
                        console.error('Error:', err);
                        alert('An error occurred while deleting the board.');
                    }
                 });
             },

             // Quick Add Task
             // Quick Add Task
             openQuickAdd(boardId) {
                 // Close any other open quick-add forms
                 if (this.quickAddOpen !== null && this.quickAddOpen !== boardId) {
                     this.quickAddOpen = null;
                 }
                 this.quickAddOpen = boardId;
                 // Focus title input after form renders
                 this.$nextTick(() => {
                     const input = document.querySelector(`[data-board-id="${boardId}"] .quick-add-form-input`);
                     if (input) input.focus();
                 });
             },

             async submitQuickAdd(boardId) {
                 const card = document.querySelector(`[data-board-id="${boardId}"]`);
                 const form = card.querySelector('.quick-add-form');
                 const formData = new FormData(form);
                 const column = formData.get('column');
                 if (!column) {
                     alert('Cannot add task: this board has no columns configured.');
                     return;
                 }
                 const submitBtn = form.querySelector('button[type="submit"]');
                 const originalHTML = submitBtn.innerHTML;

                 submitBtn.disabled = true;
                 submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin text-[10px]"></i>Saving...';

                 try {
                     const response = await fetch("0".replace('0', boardId), {
                         method: 'POST',
                         body: formData,
                         headers: {
                             'X-CSRFToken': this.getCsrfToken(),
                             'X-Requested-With': 'XMLHttpRequest'
                         }
                     });
                     const data = await response.json();
                     if (data.success) {
                         // Close quick-add form
                         this.quickAddOpen = null;
                         // Get priority to increment badge
                         const form = card.querySelector('form');
                         const priority = formData.get('priority');
                         // Update counts on card
                         this.incrementBoardCounts(boardId, priority);
                         // Optionally refresh tooltip if open
                         const tooltip = card.querySelector('.task-preview-tooltip');
                         if (tooltip && tooltip.classList.contains('show')) {
                             this.refreshTooltip(boardId);
                         }
                         showToast('Task added!', 'success');
                     } else {
                         alert(data.error || 'Failed to add task');
                     }
                 } catch (err) {
                     console.error('Error adding task:', err);
                     alert('An error occurred');
                 } finally {
                     submitBtn.disabled = false;
                     submitBtn.innerHTML = originalHTML;
                 }
             },

             incrementBoardCounts(boardId, priority) {
                 const card = document.querySelector(`[data-board-id="${boardId}"]`);
                 if (!card) return;
                 // Title mapping
                 const titleMap = {
                     high: 'High priority pending',
                     medium: 'Medium priority pending',
                     low: 'Low priority pending'
                 };
                 const title = titleMap[priority];
                 if (!title) return; // urgent not tracked
                 
                 // Increment total tasks
                 const tasksIcon = card.querySelector('.fa-tasks');
                 if (tasksIcon) {
                     const totalSpan = tasksIcon.closest('div').querySelector('.text-sm');
                     if (totalSpan) {
                         totalSpan.textContent = parseInt(totalSpan.textContent) + 1;
                     }
                 }

                 // Increment priority badge if exists; else create it
                 let badge = card.querySelector(`[title="${title}"]`);
                 if (badge) {
                     const count = parseInt(badge.textContent.trim()) || 0;
                     badge.innerHTML = `<i class="fas fa-circle text-[8px]"></i>${count + 1}`;
                 } else {
                     // Create badge and append to priority container
                     const container = card.querySelector('.flex.items-center.gap-2'); // container for priority badges
                     if (container) {
                         const color = priority === 'high' ? 'red' : priority === 'medium' ? 'yellow' : 'blue';
                         const title = titleMap[priority];
                         badge = document.createElement('span');
                         badge.className = `flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-${color}-100 dark:bg-${color}-900/30 text-${color}-700 dark:text-${color}-400`;
                         badge.setAttribute('title', title);
                         badge.innerHTML = `<i class="fas fa-circle text-[8px]"></i>1`;
                         container.appendChild(badge);
                     }
                 }
             },

             refreshTooltip(boardId) {
                 const card = document.querySelector(`[data-board-id="${boardId}"]`);
                 if (!card) return;
                 const tooltip = card.querySelector('.task-preview-tooltip');
                 if (!tooltip) return;
                 const previewUrl = card.dataset.previewUrl;
                 if (!previewUrl) return;

                 fetch(previewUrl)
                     .then(r => r.json())
                     .then(data => {
                         const colorMap = { 'urgent': '#dc2626', 'high': '#ef4444', 'medium': '#eab308', 'low': '#3b82f6' };
                         if (data.tasks && data.tasks.length > 0) {
                             tooltip.innerHTML = `
                                 <div class="p-4 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                                     <div class="flex items-center justify-between">
                                         <h4 class="text-sm font-semibold text-gray-800 dark:text-gray-200">Tasks</h4>
                                         <span class="text-xs text-gray-500 dark:text-gray-400">${data.tasks.length} total</span>
                                     </div>
                                 </div>
                                 <div class="mini-kanban-column p-2 space-y-1 max-h-48 overflow-y-auto">
                                     ${data.tasks.map(task => {
                                         const color = colorMap[task.priority] || '#6b7280';
                                         const priorityLabel = task.priority.charAt(0).toUpperCase();
                                         const dueDate = task.deadline ? new Date(task.deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : null;
                                         return `<div class="mini-task-item flex items-center gap-2 px-2 py-1.5 rounded text-sm ${task.is_completed ? 'completed' : 'text-gray-700 dark:text-gray-200'}" style="border-left: 3px solid ${color}">
                                             <input type="checkbox" ${task.is_completed ? 'checked' : ''} disabled class="w-3.5 h-3.5 accent-green-500">
                                             <span class="flex-1 truncate">${this.escapeHtml(task.title)}</span>
                                             ${dueDate ? `<span class="flex-shrink-0 px-1.5 py-0.5 rounded text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700">${dueDate}</span>` : ''}
                                             <span class="flex-shrink-0 px-1.5 py-0.5 rounded text-xs font-medium text-white" style="background-color: ${color}">${priorityLabel}</span>
                                         </div>`;
                                     }).join('')}
                                 </div>
                                   <div class="p-2 border-t border-gray-100 dark:border-gray-700 text-center bg-gray-50 dark:bg-gray-900">
                                       <a href="${card.dataset.detailUrl}" class="text-xs text-blue-600 dark:text-blue-400 hover:underline">Open Board →</a>
                                   </div>
                             `;
                         } else {
                             tooltip.innerHTML = `<div class="p-4 text-center text-gray-500 dark:text-gray-400 text-sm">No pending tasks</div>`;
                         }
                     })
                     .catch(err => {
                         console.error('Error refreshing tooltip:', err);
                         tooltip.innerHTML = `<div class="p-4 text-center text-red-500 text-sm">Failed to load</div>`;
                      });
              }

          };
      }
     // ========== Non-Alpine Global Functions ==========

    // Archive board confirmation (called from inline onsubmit)
    window.confirmArchive = function(event, boardName) {
        event.preventDefault();
        const form = event.target;

        if (window.PersonalBoardsData?.confirmModalOpen) {
            window.PersonalBoardsData.closeConfirmModal();
            return false;
        }

        window.PersonalBoardsData.openConfirmModal({
            title: 'Archive Board',
            message: `Are you sure you want to archive "${boardName}"? It will be moved to the archived list and won't appear on your main dashboard.`,
            type: 'warning',
            confirmText: 'Archive',
            iconBgClass: 'bg-yellow-500/20',
            iconClass: 'fa-archive text-yellow-500',
            buttonClass: 'bg-yellow-600 hover:bg-yellow-500 text-white focus:ring-yellow-500',
            buttonIconClass: 'fa-archive'
        }, async () => {
            try {
                const formData = new FormData(form);
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                const data = await response.json();
                if (data.success || data.archived) {
                     const match = form.action.match(/\/personal\/(\d+)\/archive\//);
                     if (match) {
                         const boardId = match[1];
                         const card = document.querySelector(`[data-board-id="${boardId}"]`);
                         if (card) {
                             card.style.transition = 'opacity 0.3s';
                             card.style.opacity = '0';
                             setTimeout(() => card.remove(), 300);
                         }
                     }
                     window.PersonalBoardsData.statsData.boards--;
                     window.PersonalBoardsData.closeConfirmModal();
                     showToast('Board archived successfully!', 'success');
                } else {
                    alert('Error: ' + (data.error || 'Failed to archive board'));
                    window.PersonalBoardsData.closeConfirmModal();
                }
            } catch (err) {
                console.error('Error:', err);
                alert('An error occurred while archiving the board.');
                window.PersonalBoardsData.closeConfirmModal();
            }
        });

        return false;
    };

    function openEditModal(boardId, name, description) {
        const modal = document.getElementById('editBoardModal');
        const editUrl = "0".replace('0', boardId);
        document.getElementById('editBoardForm').action = editUrl;
        document.getElementById('editBoardName').value = name;
        document.getElementById('editBoardDescription').value = description || '';
         modal.classList.add('is-open');
         modal.setAttribute('aria-hidden', 'false');
         document.getElementById('editBoardName').focus();
     }

     function closeEditModal() {
        document.getElementById('editBoardModal').classList.remove('is-open');
    }

    document.getElementById('editBoardForm')?.addEventListener('submit', function(e) {
        e.preventDefault();

        const form = e.target;
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalHTML = submitBtn.innerHTML;

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';

        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value,
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const match = form.action.match(/\/personal\/(\d+)\/edit\//);
                if (match) {
                    const boardId = match[1];
                    const card = document.querySelector(`[data-board-id="${boardId}"]`);
                    if (card) {
                        const titleEl = card.querySelector('h3');
                        const descEl  = card.querySelector('p');
                        if (titleEl) titleEl.textContent = formData.get('name');
                        if (descEl)  descEl.textContent  = formData.get('description') || 'Personal productivity board';
                    }
                }
                closeEditModal();
                showToast('Board updated successfully!', 'success');
            } else {
                alert('Error: ' + (data.error || 'Failed to update board'));
            }
        })
        .catch(err => {
            console.error('Error:', err);
            alert('An error occurred while updating the board.');
        })
        .finally(() => {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalHTML;
        });
    });

    // Close modal on backdrop click
    document.getElementById('editBoardModal')?.addEventListener('click', function(e) {
        if (e.target === this) closeEditModal();
    });

    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const editModal = document.getElementById('editBoardModal');
            const confirmModal = document.getElementById('confirmModal');
            if (confirmModal?.classList.contains('is-open') || window.PersonalBoardsData?.confirmModalOpen) {
                window.PersonalBoardsData?.closeConfirmModal();
            } else if (editModal?.classList.contains('is-open')) {
                closeEditModal();
            }
        }
    });

    // Create Board Form — AJAX submission
    ;(function() {
        const form = document.querySelector('#createBoardModal form');
        if (!form) return;

        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(form);
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalHTML = submitBtn.innerHTML;

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin text-[10px]"></i>Creating...';

            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                let responseText;
                try {
                    responseText = await response.text();
                } catch (e) {
                    responseText = '(could not read response)';
                }

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}\n${responseText.substring(0, 200)}`);
                }

                const data = JSON.parse(responseText);

                if (data.success) {
                    const board = data.board;

                    // Close modal and reset form immediately
                    window.PersonalBoardsData.closeCreateModal();
                    form.reset();
                    window.PersonalBoardsData.selectedTemplate = null;
                    window.PersonalBoardsData.createFormName = '';
                    window.PersonalBoardsData.createFormDesc = '';

                     // Check if grid exists (if no boards previously, grid is not rendered)
                     const grid = document.querySelector('#boards-grid');
                     const emptyState = document.querySelector('.empty-state-enhanced');

                    if (!grid) {
                        // First board — reload page to render grid + stats
                        window.location.reload();
                        return;
                    }

                    // Remove empty state if still present (safety)
                    if (emptyState) emptyState.remove();

                    // Build card HTML and prepend to grid
                    let cardHtml;
                    try {
                        cardHtml = buildBoardCard(board);
                    } catch (err) {
                        console.error('buildBoardCard error:', err);
                        throw err; // Will be caught by outer catch
                    }
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = cardHtml;
                    const newCard = tempDiv.firstElementChild;
                    grid.insertBefore(newCard, grid.firstChild);

                    // Initialize Alpine bindings for dynamic card (for @click, x-show, etc.)
                    if (window.Alpine && typeof window.Alpine.initTree === 'function') {
                        window.Alpine.initTree(newCard);
                    }

                     // Initialize micro-interactions for new card
                     window.PersonalBoardsData.initRippleEffect();
                     window.PersonalBoardsData.initMagneticDragHandle();
                     window.PersonalBoardsData.initTaskPreview();

                     // Update board count stat
                     window.PersonalBoardsData.statsData.boards++;

                     // Show success toast
                     showToast('Board created successfully!', 'success');
                }
            } catch (err) {
                console.error('Error creating board:', err);
                let errorMsg = 'An error occurred while creating the board.';
                if (err.message) errorMsg += '\n\nDetails: ' + err.message;
                alert(errorMsg);
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalHTML;
            }
        });
    })();

    // Helper: build a board card HTML string (used in AJAX create & restore)
     function buildBoardCard(board) {
         const escapedName = window.PersonalBoardsData.escapeHtml(board.name);
         const escapedDesc = window.PersonalBoardsData.escapeHtml(board.description || 'Personal productivity board');
         const escapedNameJs = window.PersonalBoardsData.escapeJs(board.name);
         // Compute task stats and progress
         const totalTasks = board.total_tasks || 0;
         const completedTasks = board.completed_tasks || 0;
         const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
         const dashArray = totalTasks > 0 ? `${progressPercent}, 100` : '0, 100';
         // Priority badges HTML
         let priorityBadgesHtml = '';
          if (board.high_priority_tasks > 0) {
              priorityBadgesHtml += `<span class="flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400" title="High priority pending"><i class="fas fa-circle text-[8px]"></i>${board.high_priority_tasks}</span>`;
          }
          if (board.medium_priority_tasks > 0) {
              priorityBadgesHtml += `<span class="flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400" title="Medium priority pending"><i class="fas fa-circle text-[8px]"></i>${board.medium_priority_tasks}</span>`;
          }
          if (board.low_priority_tasks > 0) {
              priorityBadgesHtml += `<span class="flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400" title="Low priority pending"><i class="fas fa-circle text-[8px]"></i>${board.low_priority_tasks}</span>`;
          }
         const detailUrl = "0".replace('0', board.id);
         const previewUrl = "0".replace('0', board.id);
         const archiveUrl = window.PersonalBoardsData.getArchiveUrl(board.id);
         const csrfToken = window.PersonalBoardsData.getCsrfToken();
         const color = window.PersonalBoardsData.getBoardBorderColor(board.tag || '');
         const adjustedColor = window.PersonalBoardsData.adjustColor(color, 40);
         const tagLabel = board.tag ? window.PersonalBoardsData.getTagLabel(board.tag) : '';
         const tagClass = board.tag ? window.PersonalBoardsData.getTagBadgeClass(board.tag) : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';

                 return `
             <div class="relative flip-card" data-board-id="${board.id}" data-preview-url="${previewUrl}" data-detail-url="${detailUrl}" data-board-tag="${board.tag || ''}">
                 <a href="${detailUrl}" draggable="false" class="board-card block rounded-xl p-5 bg-white dark:bg-gray-800 border border-2 shadow-md hover:shadow-xl transition-all duration-300 group cursor-pointer" style="border-color: ${color}" aria-label="Open ${escapedName} personal board">
                    <div class="absolute top-0 left-0 right-0 h-1 rounded-t-xl" style="background: linear-gradient(90deg, ${color} 0%, ${adjustedColor} 100%)"></div>
                    <div class="pt-4">
                        <div class="flex items-start mb-3">
                                <button draggable="false"
                                        @click.stop
                                        class="drag-handle flex items-center justify-center w-6 h-6 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 border border-gray-200 dark:border-gray-600 transition-all shadow-sm text-xs font-medium cursor-grab me-3 flex-shrink-0"
                                        title="Drag to reorder"
                                        aria-label="Drag to reorder ${escapedName}">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="6" r="2"></circle><circle cx="12" cy="12" r="2"></circle><circle cx="12" cy="18" r="2"></circle></svg>
                            </button>
                            <div class="flex-1 min-w-0">
                                <h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors cursor-pointer px-2 py-1 -mx-2 -my-1 rounded" data-board-id="${board.id}" data-field="name" contenteditable="false" title="Click to edit">${escapedName}</h3>
                                <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2 px-2 py-1 -mx-2 -my-1 rounded" data-board-id="${board.id}" data-field="description" contenteditable="false" title="Click to edit">${escapedDesc}</p>
                                ${board.tag ? `
                                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium mt-2 ${tagClass}">
                                    ${tagLabel}
                                </span>` : ''}
                            </div>
                        </div>
                         <div class="hidden md:flex items-center gap-4 pt-3 border-t border-gray-100 dark:border-gray-700" data-board-id="${board.id}">
                             <div class="flex items-center gap-1.5 text-gray-600 dark:text-gray-400"><i class="fas fa-tasks text-sm"></i><span class="text-sm">${totalTasks}</span></div>
                             <div class="flex items-center gap-1.5 text-green-600 dark:text-green-400"><i class="fas fa-check-circle text-sm"></i><span class="text-sm">${completedTasks}</span></div>
                             <div class="flex-1"></div>
                             <div class="flex items-center gap-2" data-priority-badges>${priorityBadgesHtml}</div>
                             <div class="flex items-center gap-2">
                                 <div class="relative w-8 h-8">
                                     <svg class="w-8 h-8" viewBox="0 0 36 36">
                                         <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" stroke-width="3" class="text-gray-200 dark:text-gray-700"></circle>
                                         <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" stroke-width="3" stroke-dasharray="${dashArray}" class="text-emerald-500 progress-ring-circle"></circle>
                                     </svg>
                                 </div>
                                 <span class="text-xs font-medium text-gray-600 dark:text-gray-400">${progressPercent}%</span>
                             </div>
                         </div>
                    </div>
                </a>
                <button class="md:hidden absolute top-3 right-14 p-1.5 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-blue-50 dark:hover:bg-blue-900/40 text-gray-500 hover:text-blue-600 dark:hover:text-blue-400 border border-gray-200 dark:border-gray-600 transition-all shadow-sm text-xs" @click="mobileStatsOpen[${board.id}] = !mobileStatsOpen[${board.id}]" :aria-expanded="mobileStatsOpen[${board.id}]" aria-label="Toggle stats for ${escapedName}">
                    <i class="fas fa-info-circle"></i>
                </button>
                <div x-show="mobileStatsOpen[${board.id}]" x-transition class="md:hidden absolute right-0 top-10 z-10 w-40 bg-white dark:bg-gray-700 rounded-lg shadow-lg border border-gray-200 dark:border-gray-600 p-3" @click.away="mobileStatsOpen[${board.id}] = false" x-cloak>
                     <div class="space-y-2">
                         <div class="flex items-center justify-between text-sm"><span class="text-gray-600 dark:text-gray-300">Tasks</span><span class="font-medium text-gray-900 dark:text-gray-100">${totalTasks}</span></div>
                         <div class="flex items-center justify-between text-sm"><span class="text-green-600 dark:text-green-400">Done</span><span class="font-medium text-green-600 dark:text-green-400">${completedTasks}</span></div>
                         <div class="flex items-center justify-between text-sm pt-2 border-t border-gray-100 dark:border-gray-600"><span class="text-gray-600 dark:text-gray-300">Progress</span><span class="font-medium text-gray-900 dark:text-gray-100">${progressPercent}%</span></div>
                     </div>
                </div>
                <div class="card-actions absolute top-3 right-3 flex items-center gap-1.5">
                    <button @click.prevent="openQuickAdd(${board.id})" class="quick-add-toggle flex items-center justify-center w-6 h-6 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-green-50 dark:hover:bg-green-900/40 text-gray-500 hover:text-green-600 dark:hover:text-green-400 border border-gray-200 dark:border-gray-600 hover:border-green-300 dark:hover:border-green-500 transition-all shadow-sm text-xs font-medium cursor-pointer" title="Quick add task" aria-label="Quick add task to ${escapedName}"><i class="fas fa-plus"></i></button>
                    <button @click.prevent="duplicateBoard(${board.id}, '${escapedNameJs}')" class="flex items-center justify-center w-6 h-6 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-purple-50 dark:hover:bg-purple-900/40 text-gray-500 hover:text-purple-600 dark:hover:text-purple-400 border border-gray-200 dark:border-gray-600 hover:border-purple-300 dark:hover:border-purple-500 transition-all shadow-sm text-xs font-medium cursor-pointer" title="Duplicate board" aria-label="Duplicate board ${escapedName}"><i class="fas fa-copy"></i></button>
                    <button onclick="event.stopPropagation(); openEditModal(${board.id}, '${escapedNameJs}', '${escapedDescJs}')" class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-blue-50 dark:hover:bg-blue-900/40 text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500 transition-all shadow-sm text-xs font-medium cursor-pointer" title="Edit board" aria-label="Edit board ${escapedName}"><i class="fas fa-edit text-xs" aria-hidden="true"></i><span>Edit</span></button>
                    <form method="post" action="${archiveUrl}" class="inline" onsubmit="return confirmArchive(event, '${escapedNameJs}')">
                        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                        <button type="submit" class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/90 dark:bg-gray-700/90 hover:bg-red-50 dark:hover:bg-red-900/40 text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 border border-gray-200 dark:border-gray-600 hover:border-red-300 dark:hover:border-red-500 transition-all shadow-sm text-xs font-medium cursor-pointer" title="Archive board" aria-label="Archive board ${escapedName}"><i class="fas fa-archive text-xs" aria-hidden="true"></i><span>Archive</span></button>
                    </form>
                </div>
                <div x-show="quickAddOpen === ${board.id}" x-transition class="absolute top-6 right-3 z-20 w-72 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 p-3" @click.away="quickAddOpen = null" x-cloak>
                    <form @submit.prevent="submitQuickAdd(${board.id})" class="space-y-2 quick-add-form">
                        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                        <input type="text" name="title" placeholder="Task title" required class="w-full px-2.5 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500 quick-add-form-input">
                        <div class="flex gap-2">
                            <select name="priority" class="flex-1 px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500">
                                <option value="low">Low</option>
                                <option value="medium" selected>Medium</option>
                                <option value="high">High</option>
                                <option value="urgent">Urgent</option>
                            </select>
                            <input type="date" name="deadline" class="flex-1 px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500">
                        </div>
                        <input type="hidden" name="column" value="${board.to_do_column_id || ''}">
                        <div class="flex justify-end gap-2">
                            <button type="button" @click="quickAddOpen = null" class="px-2.5 py-1.5 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200">Cancel</button>
                            <button type="submit" class="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors flex items-center gap-1"><i class="fas fa-plus text-[10px]"></i>Add</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }

     function toggleHelp() {
         const modal = document.getElementById('helpModal');
         if (!modal) return;
         const isOpen = modal.style.display === 'flex';
         if (isOpen) {
             modal.style.display = 'none';
         } else {
             // Close other modals/drawers via Alpine state
             if (window.PersonalBoardsData) {
                 window.PersonalBoardsData.createModalOpen = false;
                 window.PersonalBoardsData.confirmModalOpen = false;
                 window.PersonalBoardsData.archivedDrawerOpen = false;
             }
             modal.style.display = 'flex';
         }
     }

     function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 transition-all duration-300 ${
            type === 'success' ? 'bg-green-600' : 'bg-red-600'
        } text-white`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 2000);
    }

