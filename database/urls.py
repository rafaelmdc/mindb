from django.urls import path

from . import views

app_name = 'database'

urlpatterns = [
    path('', views.BrowserHomeView.as_view(), name='browser-home'),
    path('studies/', views.StudyListView.as_view(), name='study-list'),
    path('studies/<int:pk>/', views.StudyDetailView.as_view(), name='study-detail'),
    path('samples/', views.SampleListView.as_view(), name='sample-list'),
    path('samples/<int:pk>/', views.SampleDetailView.as_view(), name='sample-detail'),
    path('organisms/', views.OrganismListView.as_view(), name='organism-list'),
    path('organisms/<int:pk>/', views.OrganismDetailView.as_view(), name='organism-detail'),
    path(
        'associations/',
        views.RelativeAssociationListView.as_view(),
        name='relativeassociation-list',
    ),
    path(
        'associations/<int:pk>/',
        views.RelativeAssociationDetailView.as_view(),
        name='relativeassociation-detail',
    ),
]
