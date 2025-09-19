# project/urls.py
from django.urls import path
from . import views  # project/views.py에서 가져오기

urlpatterns = [
    path('', views.index, name='index'),
]
