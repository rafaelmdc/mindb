from django.urls import path

from .views import DirectionalTaxonNetworkView, GraphView, HomeView, ModelDiagramDownloadView, ModelDiagramView, StaffHomeView

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('graph/', GraphView.as_view(), name='graph'),
    path('graph/directional-taxa/', DirectionalTaxonNetworkView.as_view(), name='directional-taxon-network'),
    path('staff/', StaffHomeView.as_view(), name='staff-home'),
    path('staff/models/', ModelDiagramView.as_view(), name='model-diagram'),
    path('staff/models/download/<str:output_format>/', ModelDiagramDownloadView.as_view(), name='model-diagram-download'),
]
