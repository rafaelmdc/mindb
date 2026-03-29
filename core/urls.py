from django.urls import path
from django.views.generic import RedirectView

from .views import DirectionalTaxonNetworkView, GraphView, HomeView, ModelDiagramDownloadView, ModelDiagramView, StaffHomeView

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('graph/', RedirectView.as_view(pattern_name='core:disease-network', permanent=False)),
    path('graph/disease/', GraphView.as_view(), name='disease-network'),
    path('graph/directional-taxa/', RedirectView.as_view(pattern_name='core:co-abundance-network', permanent=False)),
    path('graph/co-abundance/', DirectionalTaxonNetworkView.as_view(), name='co-abundance-network'),
    path('staff/', StaffHomeView.as_view(), name='staff-home'),
    path('staff/models/', ModelDiagramView.as_view(), name='model-diagram'),
    path('staff/models/download/<str:output_format>/', ModelDiagramDownloadView.as_view(), name='model-diagram-download'),
]
