from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('new/', views.new, name='new'),
    path('add/', views.add, name='add'),
    path('history/', views.history, name='history'),
    path('inventory/', views.inventory, name='inventory'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('archives/', views.archives, name='archives'),
    path('item/<int:item_id>/archive/', views.archive_item, name='archive_item'),
    path('batch/<int:batch_id>/archive/', views.archive_batch, name='archive_batch'),
    path('item/<int:item_id>/restore/', views.restore_item, name='restore_item'),
    path('batch/<int:batch_id>/restore/', views.restore_batch, name='restore_batch'),
    path('item/<int:item_id>/delete/', views.delete_item_permanent, name='delete_item_permanent'),
    path('batch/<int:batch_id>/delete/', views.delete_batch_permanent, name='delete_batch_permanent'),
]
