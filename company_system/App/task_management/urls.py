from django.urls import path
from . import views

app_name = 'task_management'

urlpatterns = [
    # Board URLs
    path('boards/', views.board_list, name='board_list'),
    path('boards/create/', views.board_create, name='board_create'),
    path('boards/<int:board_id>/', views.board_detail, name='board_detail'),
    path('boards/<int:board_id>/delete/', views.board_delete, name='board_delete'),

    # Column URLs
    path('boards/<int:board_id>/column/create/', views.column_create, name='column_create'),
    path('columns/<int:column_id>/delete/', views.column_delete, name='column_delete'),

    # Task URLs
    path('boards/<int:board_id>/task/create/', views.task_create, name='task_create'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('tasks/<int:task_id>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:task_id>/delete/', views.task_delete, name='task_delete'),

    # API URLs
    path('api/update-position/', views.api_update_task_position, name='api_update_position'),
    path('api/boards/<int:board_id>/tasks/', views.api_get_tasks, name='api_get_tasks'),

    # Roadmap URLs
    path('roadmaps/', views.roadmap_list, name='roadmap_list'),
    path('roadmaps/create/', views.roadmap_create, name='roadmap_create'),
    path('roadmaps/<int:roadmap_id>/', views.roadmap_detail, name='roadmap_detail'),
    path('roadmaps/<int:roadmap_id>/delete/', views.roadmap_delete, name='roadmap_delete'),
    path('roadmaps/<int:roadmap_id>/timeline/', views.timeline_view, name='timeline_view'),
    path('roadmaps/<int:roadmap_id>/task/create/', views.roadmap_task_create, name='roadmap_task_create'),

    # Personal Productivity URLs
    path('personal/', views.personal_board_list, name='personal_board_list'),
    path('personal/help/', views.help_index, name='help_index'),
    path('personal/create/', views.personal_board_create, name='personal_board_create'),
    path('personal/<int:board_id>/', views.personal_board_detail, name='personal_board_detail'),
    path('personal/<int:board_id>/edit/', views.personal_board_edit, name='personal_board_edit'),
    path('personal/<int:board_id>/archive/', views.personal_board_archive, name='personal_board_archive'),
    path('personal/<int:board_id>/restore/', views.personal_board_restore, name='personal_board_restore'),
    path('personal/<int:board_id>/duplicate/', views.personal_board_duplicate, name='personal_board_duplicate'),
    path('personal/<int:board_id>/delete/', views.personal_board_delete_permanent, name='personal_board_delete_permanent'),
     path('personal/archived/', views.personal_board_archived_list, name='personal_board_archived_list'),
     path('personal/archived/api/', views.personal_board_archived_api, name='personal_board_archived_api'),
      path('personal/reorder/', views.personal_board_reorder, name='personal_board_reorder'),
      path('personal/<int:board_id>/api/tasks-preview/', views.personal_tasks_preview_api, name='personal_tasks_preview_api'),
      path('personal/<int:board_id>/task/create/', views.personal_task_create, name='personal_task_create'),
    path('personal/tasks/<int:task_id>/toggle/', views.personal_task_toggle, name='personal_task_toggle'),
    path('personal/tasks/<int:task_id>/archive/', views.personal_task_archive, name='personal_task_archive'),
    path('personal/tasks/<int:task_id>/restore/', views.personal_task_restore, name='personal_task_restore'),
    path('personal/tasks/<int:task_id>/list-archived/', views.personal_task_list_archived, name='personal_task_list_archived'),
    path('personal/tasks/<int:task_id>/delete/', views.personal_task_delete, name='personal_task_delete'),
    path('personal/tasks/<int:task_id>/edit/', views.personal_task_edit, name='personal_task_edit'),
    path('personal/tasks/<int:task_id>/update-notes/', views.personal_task_update_notes, name='personal_task_update_notes'),
    path('personal/tasks/<int:task_id>/checklist/add/', views.personal_task_checklist_add, name='personal_task_checklist_add'),
    path('personal/checklist/<int:item_id>/toggle/', views.personal_task_checklist_toggle, name='personal_task_checklist_toggle'),
    path('personal/checklist/<int:item_id>/delete/', views.personal_task_checklist_delete, name='personal_task_checklist_delete'),
    path('personal/checklist/<int:item_id>/rename/', views.personal_task_checklist_rename, name='personal_task_checklist_rename'),
    path('personal/tasks/<int:task_id>/checklist/reorder/', views.personal_task_checklist_reorder, name='personal_task_checklist_reorder'),
    path('personal/tasks/<int:task_id>/set_priority/', views.personal_task_set_priority, name='personal_task_set_priority'),
    path('personal/api/update-position/', views.personal_task_update_position, name='personal_task_update_position'),

    # Personal Column URLs
    path('personal/<int:board_id>/column/create/', views.personal_column_create, name='personal_column_create'),
    path('personal/columns/<int:column_id>/edit/', views.personal_column_edit, name='personal_column_edit'),
    path('personal/columns/<int:column_id>/delete/', views.personal_column_delete, name='personal_column_delete'),
    path('personal/api/update-column-position/', views.personal_column_update_position, name='personal_column_update_position'),

    # Task Checklist & Comments URLs
    path('tasks/<int:task_id>/checklist/add/', views.task_checklist_add, name='task_checklist_add'),
    path('checklist/<int:item_id>/toggle/', views.task_checklist_toggle, name='task_checklist_toggle'),
    path('checklist/<int:item_id>/delete/', views.task_checklist_delete, name='task_checklist_delete'),
    path('tasks/<int:task_id>/comment/add/', views.task_comment_add, name='task_comment_add'),
    path('comments/<int:comment_id>/delete/', views.task_comment_delete, name='task_comment_delete'),
]