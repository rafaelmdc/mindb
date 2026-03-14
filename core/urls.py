from django.urls import path

from .views import GraphView, HomeView, ModelDiagramView, StaffHomeView

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('graph/', GraphView.as_view(), name='graph'),
    path('staff/', StaffHomeView.as_view(), name='staff-home'),
    path('staff/models/', ModelDiagramView.as_view(), name='model-diagram'),
]
