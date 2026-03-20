from django.urls import path
from . import views

urlpatterns = [
    path('', views.logowanie, name='login'),
    path('rejestracja/', views.rejestracja, name='rejestracja'),
    path('wyloguj/', views.wylogowanie, name='wyloguj'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('pomiary/', views.pomiary, name='pomiary'),
    path('lekarz/', views.panel_lekarza, name='panel_lekarza'),
    path('lekarz/pacjentka/<int:pacjentka_id>/',
         views.szczegoly_pacjentki, name='szczegoly_pacjentki'),
]