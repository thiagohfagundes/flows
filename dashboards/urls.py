from django.contrib import admin
from django.urls import path, include
from . import views

app_name = "dashboards"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
]