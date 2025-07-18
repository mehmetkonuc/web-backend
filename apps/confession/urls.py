from django.urls import path
from . import views

app_name = 'confession'

urlpatterns = [
    # Main confession list
    path('', views.ConfessionListView.as_view(), name='confession_list'),
    
    # Confession detail
    path('<int:pk>/', views.ConfessionDetailView.as_view(), name='confession_detail'),
    
    # Category-based confession list
    path('category/<int:pk>/', views.ConfessionCategoryView.as_view(), name='confession_category'),
    
    # Create confession
    path('create/', views.ConfessionCreateView.as_view(), name='confession_create'),
    
    # Update confession
    path('<int:pk>/update/', views.ConfessionUpdateView.as_view(), name='confession_update'),
    
    # Delete confession
    path('<int:pk>/delete/', views.ConfessionDeleteView.as_view(), name='confession_delete'),
    path('clear-filters/', views.clear_filters_view, name='clear_filters'),

    # AJAX endpoints
    path('<int:pk>/toggle-privacy/', views.confession_toggle_privacy, name='confession_toggle_privacy'),
    path('<int:pk>/toggle-active/', views.confession_toggle_active, name='confession_toggle_active'),
]