from django.urls import path
from . import views

urlpatterns = [
    # Logowanie i rejestracja
    path('', views.logowanie, name='login'),
    path('rejestracja/', views.rejestracja, name='rejestracja'),
    path('wyloguj/', views.wylogowanie, name='wyloguj'),

    # Panel pacjentki
    path('dashboard/', views.dashboard, name='dashboard'),
    path('pomiary/', views.pomiary, name='pomiary'),

        # Część 5 – eksport, wykres, PDF
    path('eksport/xlsx/', views.eksport_xlsx, name='eksport_xlsx'),
    path('wykres/png/', views.wykres_png, name='wykres_png'),
    path('badania/', views.badania_pdf, name='badania_pdf'),
    path('badania/<int:plik_id>/usun/', views.usun_pdf, name='usun_pdf'),
    
    
    # Panel lekarza
    path('lekarz/', views.panel_lekarza, name='panel_lekarza'),
    path('lekarz/pacjentka/<int:pacjentka_id>/',
         views.szczegoly_pacjentki, name='szczegoly_pacjentki'),
]