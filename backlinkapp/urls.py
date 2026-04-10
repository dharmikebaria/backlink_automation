# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('logout/', views.logout_view, name='logout'),
    path('load-excel/', views.load_excel_view, name='load_excel'),
    path('upload-excel/', views.upload_excel_view, name='upload_excel'),
    path('upload-csv/', views.upload_csv_view, name='upload_csv'),
    path('run/', views.run_automation_view, name='run_automation'),
    path('success/', views.success_page_view, name='success_page'),
    path('credential/add/', views.add_credential_view, name='add_credential'),
    path('credential/edit/', views.edit_credential_view, name='edit_credential'),
    path('credential/delete/', views.delete_credential_view, name='delete_credential'),
    path('blog/update/', views.blog_update_view, name='blog_update'),
    path('history/', views.history_view, name='history'),
    path('history/delete/', views.history_delete_view, name='history_delete'),
    path('history/bulk-delete/', views.history_bulk_delete_view, name='history_bulk_delete'),
    path('images/', views.image_manager_view, name='image_manager'),
    path('images/file/<path:filename>', views.serve_image_view, name='serve_image'),
]
