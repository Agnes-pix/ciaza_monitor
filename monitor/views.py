from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from .decorators import tylko_pacjentka, tylko_lekarz
from .models import Pacjentka, Pomiar, WizytaLekarska, Recepta, PacjentkaLekarza
from .forms import (
    FormularzRejestracji,
    FormularzDanePacjentki,
    FormularzDaneLekarz,
    FormularzPomiaru,
    FormularzSamopoczucia,
    FormularzRecepty,
    FormularzReceptyDlaPacjentki,
    FormularzWizytyDlaPacjentki,
    FormularzDodajPacjentkePesel,
)


# ================================================================
# WIDOK – Logowanie
# GET: pokazuje formularz logowania
# POST: weryfikuje dane i przekierowuje wg roli
# ================================================================
def logowanie(request):
    if request.method == 'POST':
        formularz = AuthenticationForm(data=request.POST)
        if formularz.is_valid():
            user = formularz.get_user()
            login(request, user)
            return redirect('panel_lekarza' if user.is_staff else 'dashboard')
    else:
        formularz = AuthenticationForm()
    return render(request, 'monitor/logowanie.html', {
        'formularz': formularz
    })


# ================================================================
# WIDOK – Wylogowanie
# Czyści sesję i przekierowuje na stronę logowania
# ================================================================
def wylogowanie(request):
    logout(request)
    return redirect('login')


# ================================================================
# WIDOK – Rejestracja
# GET: pokazuje formularz rejestracji
# POST: tworzy konto użytkownika i profil (pacjentki lub lekarza)
# Rola wybierana przez pole radio w formularzu
# ================================================================
def rejestracja(request):
    if request.method == 'POST':
        rola = request.POST.get('rola', 'pacjentka')
        f_user = FormularzRejestracji(request.POST)

        if rola == 'pacjentka':
            f_dane_pacjentka = FormularzDanePacjentki(request.POST)
            f_dane_lekarz = FormularzDaneLekarz()

            if f_user.is_valid() and f_dane_pacjentka.is_valid():
                user = f_user.save()
                pacjentka = f_dane_pacjentka.save(commit=False)
                pacjentka.uzytkownik = user
                pacjentka.save()
                login(request, user)
                return redirect('dashboard')

        else:
            f_dane_pacjentka = FormularzDanePacjentki()
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


# ================================================================
# WIDOK – Dashboard pacjentki (strona główna)
# Dostępny tylko dla zalogowanych pacjentek
# Pokazuje: odliczanie do porodu, recepty, wizyty, ostatnie pomiary
# ================================================================
@tylko_pacjentka
def dashboard(request):
    pacjentka = request.user.pacjentka
    dzisiaj = timezone.now().date()
    dni_do_porodu = (pacjentka.przewidywana_data_porodu - dzisiaj).days

    return render(request, 'monitor/dashboard.html', {
        'pacjentka': pacjentka,
        'dni_do_porodu': dni_do_porodu,
        'wizyty': WizytaLekarska.objects.filter(
            pacjentka=pacjentka
        ).order_by('data_wizyty'),
        'recepty': pacjentka.recepty.filter(do_zrealizowania=True),
        # Ostatnie pomiary bez ciśnień i samopoczucia
        'ostatnie_pomiary': pacjentka.pomiary.exclude(
            typ__in=['samopoczucie', 'cisnienie_s', 'cisnienie_r']
        )[:3],
        # Ciśnienia osobno – łączone w szablonie jako pary 120/80
        'ostatnie_cisnienia_s': pacjentka.pomiary.filter(
            typ='cisnienie_s'
        ).order_by('-data_pomiaru')[:3],
        'ostatnie_cisnienia_r': pacjentka.pomiary.filter(
            typ='cisnienie_r'
        ).order_by('-data_pomiaru')[:3],
    })


# ================================================================
# WIDOK – Pomiary pacjentki
# Dostępny tylko dla zalogowanych pacjentek
# GET: pokazuje formularz i historię pomiarów
# POST: zapisuje nowy pomiar lub samopoczucie
#
# Logika ciśnienia:
# - pacjentka wpisuje format 120/80
# - widok rozdziela na dwa rekordy: cisnienie_s i cisnienie_r
# - w szablonie łączone z powrotem jako para do wyświetlenia
# ================================================================
@tylko_pacjentka
def pomiary(request):
    pacjentka = request.user.pacjentka

    if request.method == 'POST':
        akcja = request.POST.get('akcja')

        if akcja == 'dodaj_pomiar':
            f = FormularzPomiaru(request.POST)
            if f.is_valid():
                typ = f.cleaned_data['typ']
                data_pomiaru = f.cleaned_data['data_pomiaru']

                if typ == 'cisnienie':
                    # Rozdzielamy format 120/80 na dwa osobne rekordy
                    czesci = f.cleaned_data['cisnienie'].split('/')
                    Pomiar.objects.create(
                        pacjentka=pacjentka,
                        typ='cisnienie_s',
                        wartosc=float(czesci[0].strip()),
                        data_pomiaru=data_pomiaru
                    )
                    Pomiar.objects.create(
                        pacjentka=pacjentka,
                        typ='cisnienie_r',
                        wartosc=float(czesci[1].strip()),
                        data_pomiaru=data_pomiaru
                    )
                else:
                    pomiar = f.save(commit=False)
                    pomiar.pacjentka = pacjentka
                    pomiar.save()
                return redirect('pomiary')

        elif akcja == 'dodaj_samopoczucie':
            f = FormularzSamopoczucia(request.POST)
            if f.is_valid():
                wpis = f.save(commit=False)
                wpis.pacjentka = pacjentka
                wpis.typ = 'samopoczucie'
                wpis.wartosc = f.cleaned_data['samopoczucie']
                wpis.save()
                return redirect('pomiary')

    # Funkcja pomocnicza do pobierania danych dla wykresów
    def pobierz_dane(typ):
        rekordy = Pomiar.objects.filter(
            pacjentka=pacjentka, typ=typ
        ).order_by('data_pomiaru').values_list('data_pomiaru', 'wartosc')
        return {
            'etykiety': [r[0].strftime('%d.%m %H:%M') for r in rekordy],
            'wartosci': [r[1] for r in rekordy],
        }

    return render(request, 'monitor/pomiary.html', {
        'f_pomiar': FormularzPomiaru(),
        'f_samopoczucie': FormularzSamopoczucia(),
        # Pomiary bez ciśnień i samopoczucia
        'historia_pomiarow': pacjentka.pomiary.exclude(
            typ__in=['samopoczucie', 'cisnienie_s', 'cisnienie_r']
        ),
        # Ciśnienia osobno – łączone w szablonie jako pary
        'historia_cisnienia': pacjentka.pomiary.filter(
            typ='cisnienie_s'
        ).order_by('-data_pomiaru'),
        'historia_cisnienia_r': pacjentka.pomiary.filter(
            typ='cisnienie_r'
        ).order_by('-data_pomiaru'),
        'historia_samopoczucia': pacjentka.pomiary.filter(
            typ='samopoczucie'
        ).order_by('-data_pomiaru')[:10],
        # Dane do wykresów Chart.js
        'dane_glukoza': pobierz_dane('glukoza'),
        'dane_cisnienie_s': pobierz_dane('cisnienie_s'),
        'dane_cisnienie_r': pobierz_dane('cisnienie_r'),
    })


# ================================================================
# WIDOK – Panel lekarza
# Dostępny tylko dla zalogowanych lekarzy
# GET: pokazuje listę swoich pacjentek
# POST: obsługuje dodanie pacjentki po PESEL
# ================================================================
@tylko_lekarz
def panel_lekarza(request):
    komunikat = None

    if request.method == 'POST':
        akcja = request.POST.get('akcja')

        if akcja == 'dodaj_pacjentke':
            f = FormularzDodajPacjentkePesel(request.POST)
            if f.is_valid():
                pesel = f.cleaned_data['pesel']
                try:
                    pacjentka = Pacjentka.objects.get(pesel=pesel)
                    _, utworzono = PacjentkaLekarza.objects.get_or_create(
                        lekarz=request.user,
                        pacjentka=pacjentka
                    )
                    komunikat = (
                        f'Pacjentka {pacjentka} została dodana!'
                        if utworzono
                        else 'Ta pacjentka jest już na Twojej liście!'
                    )
                except Pacjentka.DoesNotExist:
                    f.add_error('pesel',
                                'Nie znaleziono pacjentki z tym numerem PESEL!')

            return render(request, 'monitor/panel_lekarza.html', {
                'pacjentki': PacjentkaLekarza.objects.filter(
                    lekarz=request.user
                ),
                'f_dodaj_pacjentke': f,
                'komunikat': komunikat,
            })

    return render(request, 'monitor/panel_lekarza.html', {
        'pacjentki': PacjentkaLekarza.objects.filter(lekarz=request.user),
        'f_dodaj_pacjentke': FormularzDodajPacjentkePesel(),
        'komunikat': komunikat,
    })


# ================================================================
# WIDOK – Szczegóły pacjentki (widok lekarza)
# Dostępny tylko dla lekarza który ma tę pacjentkę na swojej liście
# GET: pokazuje dane pacjentki, pomiary, wykresy, formularze
# POST: obsługuje wypisanie recepty lub umówienie wizyty
# ================================================================
@tylko_lekarz
def szczegoly_pacjentki(request, pacjentka_id):
    # Sprawdzamy że lekarz ma tę pacjentkę na swojej liście
    relacja = get_object_or_404(
        PacjentkaLekarza,
        lekarz=request.user,
        pacjentka__id=pacjentka_id
    )
    pacjentka = relacja.pacjentka

    if request.method == 'POST':
        akcja = request.POST.get('akcja')

        if akcja == 'wypisz_recepte':
            f = FormularzReceptyDlaPacjentki(request.POST)
            if f.is_valid():
                recepta = f.save(commit=False)
                recepta.lekarz = request.user
                recepta.save()
                # Przypisujemy receptę do tej konkretnej pacjentki
                recepta.pacjentki.add(pacjentka)
                return redirect('szczegoly_pacjentki',
                                pacjentka_id=pacjentka_id)

        elif akcja == 'umow_wizyte':
            f = FormularzWizytyDlaPacjentki(request.POST)
            if f.is_valid():
                wizyta = f.save(commit=False)
                wizyta.lekarz = request.user
                wizyta.pacjentka = pacjentka
                wizyta.save()
                return redirect('szczegoly_pacjentki',
                                pacjentka_id=pacjentka_id)

    # Funkcja pomocnicza do pobierania danych dla wykresów
    def pobierz_dane(typ):
        rekordy = Pomiar.objects.filter(
            pacjentka=pacjentka, typ=typ
        ).order_by('data_pomiaru').values_list('data_pomiaru', 'wartosc')
        return {
            'etykiety': [r[0].strftime('%d.%m %H:%M') for r in rekordy],
            'wartosci': [r[1] for r in rekordy],
        }

    return render(request, 'monitor/szczegoly_pacjentki.html', {
        'pacjentka': pacjentka,
        'f_recepta': FormularzReceptyDlaPacjentki(),
        'f_wizyta': FormularzWizytyDlaPacjentki(),
        # Pomiary bez ciśnień i samopoczucia
        'pomiary': pacjentka.pomiary.exclude(
            typ__in=['samopoczucie', 'cisnienie_s', 'cisnienie_r']
        ),
        # Ciśnienia osobno – łączone w szablonie jako pary
        'historia_cisnienia': pacjentka.pomiary.filter(
            typ='cisnienie_s'
        ).order_by('-data_pomiaru'),
        'historia_cisnienia_r': pacjentka.pomiary.filter(
            typ='cisnienie_r'
        ).order_by('-data_pomiaru'),
        'historia_samopoczucia': pacjentka.pomiary.filter(
            typ='samopoczucie'
        ).order_by('-data_pomiaru'),
        'wizyty': pacjentka.wizyty.all(),
        'recepty': pacjentka.recepty.all(),
        # Dane do wykresów Chart.js
        'dane_glukoza': pobierz_dane('glukoza'),
        'dane_cisnienie_s': pobierz_dane('cisnienie_s'),
        'dane_cisnienie_r': pobierz_dane('cisnienie_r'),
    })