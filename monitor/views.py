from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from .models import Pacjentka, Pomiar, WizytaLekarska, Recepta, Lekarz
from .forms import (FormularzRejestracji, FormularzDanePacjentki,
                    FormularzPomiaru, FormularzWizyty,
                    FormularzRecepty, FormularzWizytyLekarza,
                    FormularzDaneLekarz) 
from .decorators import tylko_pacjentka, tylko_lekarz

def logowanie(request):
    if request.method == 'POST':
        formularz = AuthenticationForm(data=request.POST)
        if formularz.is_valid():
            user = formularz.get_user()
            login(request, user)
            return redirect('panel_lekarza' if user.is_staff else 'dashboard')
    else:
        formularz = AuthenticationForm()
    return render(request, 'monitor/logowanie.html', {'formularz': formularz})

# WYLOGOWANIE
def wylogowanie(request):
    logout(request)
    return redirect('login')


# REJESTRACJA
def rejestracja(request):
    if request.method == 'POST':
        rola = request.POST.get('rola', 'pacjentka')
        f_user = FormularzRejestracji(request.POST)

        if rola == 'pacjentka':
            f_dane_pacjentka = FormularzDanePacjentki(request.POST)
            f_dane_lekarz = FormularzDaneLekarz()  # pusty – nie waliduj

            if f_user.is_valid() and f_dane_pacjentka.is_valid():
                user = f_user.save()
                pacjentka = f_dane_pacjentka.save(commit=False)
                pacjentka.uzytkownik = user
                pacjentka.save()
                login(request, user)
                return redirect('dashboard')

        else:
            f_dane_pacjentka = FormularzDanePacjentki()  # pusty – nie waliduj
            f_dane_lekarz = FormularzDaneLekarz(request.POST)

            if f_user.is_valid() and f_dane_lekarz.is_valid():
                user = f_user.save()
                lekarz = f_dane_lekarz.save(commit=False)
                lekarz.uzytkownik = user
                lekarz.save()
                login(request, user)
                return redirect('panel_lekarza')

    else:
        f_user = FormularzRejestracji()
        f_dane_pacjentka = FormularzDanePacjentki()
        f_dane_lekarz = FormularzDaneLekarz()

    return render(request, 'monitor/rejestracja.html', {
        'f_user': f_user,
        'f_dane_pacjentka': f_dane_pacjentka,
        'f_dane_lekarz': f_dane_lekarz,
    })

    #     if f_user.is_valid() and f_dane.is_valid():
    #         user = f_user.save()
    #         pacjentka = f_dane.save(commit=False)
    #         pacjentka.uzytkownik = user
    #         pacjentka.save()
    #         login(request, user)
    #         return redirect('dashboard')
    # else:
    #     f_user = FormularzRejestracji()
    #     f_dane = FormularzDanePacjentki()
    # return render(request, 'monitor/rejestracja.html', {
    #     'f_user': f_user,
    #     'f_dane': f_dane,
    # })


# DASHBOARD – strona główna pacjentki
@tylko_pacjentka
def dashboard(request):
    pacjentka = request.user.pacjentka
    dzisiaj = timezone.now().date()
    dni_do_porodu = (pacjentka.przewidywana_data_porodu - dzisiaj).days

    nadchodzace_wizyty = WizytaLekarska.objects.filter(
        pacjentka=pacjentka,
        data_wizyty__gte=timezone.now(),
        odbyta=False
    )[:5]

    recepty = pacjentka.recepty.filter(do_zrealizowania=True)
    ostatnie_pomiary = pacjentka.pomiary.all()[:3]

    return render(request, 'monitor/dashboard.html', {
        'pacjentka': pacjentka,
        'dni_do_porodu': dni_do_porodu,
        'nadchodzace_wizyty': nadchodzace_wizyty,
        'recepty': recepty,
        'ostatnie_pomiary': ostatnie_pomiary,
    })


# POMIARY – zakładka 2
@tylko_pacjentka
def pomiary(request):
    pacjentka = request.user.pacjentka

    if request.method == 'POST':
        akcja = request.POST.get('akcja')
        if akcja == 'dodaj_pomiar':
            f = FormularzPomiaru(request.POST)
            if f.is_valid():
                pomiar = f.save(commit=False)
                pomiar.pacjentka = pacjentka
                pomiar.save()
                return redirect('pomiary')
        elif akcja == 'dodaj_wizyte':
            f = FormularzWizyty(request.POST)
            if f.is_valid():
                wizyta = f.save(commit=False)
                wizyta.pacjentka = pacjentka
                wizyta.save()
                return redirect('pomiary')

    # Pobieramy dane do wykresu z bazy
    # values_list = pobierz tylko te dwa pola zamiast całych obiektów
    def pobierz_dane(typ):
        rekordy = Pomiar.objects.filter(
            pacjentka=pacjentka,
            typ=typ
        ).order_by('data_pomiaru').values_list('data_pomiaru', 'wartosc')
        return {
            # Formatujemy daty na stringi bo JS nie rozumie dat Pythona
            'etykiety': [r[0].strftime('%d.%m %H:%M') for r in rekordy],
            'wartosci': [r[1] for r in rekordy],
        }

    return render(request, 'monitor/pomiary.html', {
        'f_pomiar': FormularzPomiaru(),
        'f_wizyta': FormularzWizyty(),
        'historia_pomiarow': pacjentka.pomiary.all(),
        'historia_wizyt': pacjentka.wizyty.all(),
        # Dane do wykresu
        'dane_glukoza': pobierz_dane('glukoza'),
        'dane_cisnienie_s': pobierz_dane('cisnienie_s'),
        'dane_cisnienie_r': pobierz_dane('cisnienie_r'),
        'dane_waga': pobierz_dane('waga'),
    })

# PANEL LEKARZA
@tylko_lekarz
def panel_lekarza(request):
    if request.method == 'POST':
        akcja = request.POST.get('akcja')
        if akcja == 'wypisz_recepte':
            f = FormularzRecepty(request.POST)
            if f.is_valid():
                recepta = f.save(commit=False)
                recepta.lekarz = request.user
                recepta.save()
                f.save_m2m()
                return redirect('panel_lekarza')
        elif akcja == 'umow_wizyte':
            f = FormularzWizytyLekarza(request.POST)
            if f.is_valid():
                wizyta = f.save(commit=False)
                wizyta.lekarz = request.user
                wizyta.save()
                return redirect('panel_lekarza')

    return render(request, 'monitor/panel_lekarza.html', {
        'pacjentki': Pacjentka.objects.all(),
        'f_recepta': FormularzRecepty(),
        'f_wizyta': FormularzWizytyLekarza(),
        'wszystkie_wizyty': WizytaLekarska.objects.all().order_by('data_wizyty'),
    })


# SZCZEGÓŁY PACJENTKI – dla lekarza
@tylko_lekarz
def szczegoly_pacjentki(request, pacjentka_id):
    pacjentka = get_object_or_404(Pacjentka, id=pacjentka_id)
    return render(request, 'monitor/szczegoly_pacjentki.html', {
        'pacjentka': pacjentka,
        'pomiary': pacjentka.pomiary.all(),
        'wizyty': pacjentka.wizyty.all(),
        'recepty': pacjentka.recepty.all(),
    })