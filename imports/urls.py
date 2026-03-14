from django.urls import path

from . import views

app_name = 'imports'

urlpatterns = [
    path('', views.upload_csv, name='upload'),
    path('preview/', views.preview_csv, name='preview'),
    path('confirm/', views.confirm_csv, name='confirm'),
    path('result/<int:batch_id>/', views.import_result, name='result'),
]
