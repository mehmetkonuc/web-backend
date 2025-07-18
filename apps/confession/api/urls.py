from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# Router için ViewSet'leri kaydet
router = DefaultRouter()
router.register(r'confessions', views.ConfessionViewSet, basename='confession')
router.register(r'filter-preferences', views.ConfessionFilterPreferencesViewSet, basename='confession-filter-preferences')

urlpatterns = [
    # Filter & Options endpoints
    path('filter-options/', views.FilterOptionsAPIView.as_view(), name='confession-filter-options'),
    
    # Category endpoints
    path('categories/', views.ConfessionCategoryListView.as_view(), name='confession-categories'),
    path('categories/popular/', views.PopularCategoriesView.as_view(), name='popular-categories'),
    
    # Router URLs (ViewSet endpoints)
    path('', include(router.urls)),
]

# Router tarafından oluşturulan URL'ler:
# 
# ConfessionViewSet endpoints:
# GET    /confessions/                     - List confessions (with filtering)
# POST   /confessions/                     - Create new confession
# GET    /confessions/{id}/                - Get specific confession
# PUT    /confessions/{id}/                - Update confession (full)
# PATCH  /confessions/{id}/                - Update confession (partial)
# DELETE /confessions/{id}/                - Delete confession (soft delete)
#
# Custom actions:
# GET    /confessions/trending/            - Get trending confessions (last 24h)
# GET    /confessions/by_category/         - Get confessions by category (?category_id=X)
# GET    /confessions/by_university/       - Get confessions by university (?university_id=X)
# GET    /confessions/my_confessions/      - Get current user's confessions
# GET    /confessions/user_confessions/    - Get specific user's confessions (?username=X)
# GET    /confessions/anonymous/           - Get only anonymous confessions
# GET    /confessions/open/                - Get only open confessions
# POST   /confessions/{id}/toggle_privacy/ - Toggle confession privacy
# GET    /confessions/stats/               - Get confession statistics
#
# ConfessionFilterPreferencesViewSet endpoints:
# GET    /filter-preferences/              - Get current user's filter preferences
# POST   /filter-preferences/              - Create/update filter preferences
# PUT    /filter-preferences/              - Update filter preferences
# PATCH  /filter-preferences/              - Update filter preferences (partial)
# POST   /filter-preferences/clear/        - Clear all filter preferences
