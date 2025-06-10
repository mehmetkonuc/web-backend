from django.urls import path
from .views import MemberListView, clear_filters_view

app_name = 'members'

urlpatterns = [
    path('', MemberListView.as_view(), name='members_list'),
    path('clear-filters/', clear_filters_view, name='clear_filters'),
]