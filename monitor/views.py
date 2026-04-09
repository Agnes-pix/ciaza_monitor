from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from .decorators import tylko_pacjentka, tylko_lekarz
from .models import Pacjentka, Pomiar, WizytaLekarska, Recepta, Lekarz, PacjentkaLekarza
from .forms import (FormularzRejestracji, FormularzDanePacjentki,
                    FormularzPomiaru, FormularzWizyty,
                    FormularzRecepty, FormularzWizytyLekarza,
                    FormularzDaneLekarz, FormularzDodajPacjentkePesel, FormularzSamopoczucia, FormularzReceptyDlaPacjentki)


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

    # Pobierz wszystkie wizyty umawianie przez lekarza
    wizyty = WizytaLekarska.objects.filter(
        pacjentka=pacjentka
    ).order_by('data_wizyty')

    recepty = pacjentka.recepty.filter(do_zrealizowania=True)


    ostatnie_pomiary = pacjentka.pomiary.exclude(
        typ__in=['samopoczucie', 'cisnienie_s', 'cisnienie_r']
    )[:3]

        # Ciśnienia do połączenia w widoku
    ostatnie_cisnienia_s = pacjentka.pomiary.filter(
        typ='cisnienie_s'
    ).order_by('-data_pomiaru')[:3]

    ostatnie_cisnienia_r = pacjentka.pomiary.filter(
        typ='cisnienie_r'
    ).order_by('-data_pomiaru')[:3]

    return render(request, 'monitor/dashboard.html', {
        'pacjentka': pacjentka,
        'dni_do_porodu': dni_do_porodu,
        'wizyty': wizyty,
        'recepty': recepty,
        'ostatnie_pomiary': ostatnie_pomiary,
        'ostatnie_cisnienia_s': ostatnie_cisnienia_s,
        'ostatnie_cisnienia_r': ostatnie_cisnienia_r,
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
                typ = f.cleaned_data['typ']
                data_pomiaru = f.cleaned_data['data_pomiaru']

                if typ == 'cisnienie':
                    # Rozdzielamy ciśnienie na dwa osobne pomiary
                    cisnienie = f.cleaned_data['cisnienie']
                    czesci = cisnienie.split('/')
                    skurczowe = float(czesci[0].strip())
                    rozkurczowe = float(czesci[1].strip())

                    # Zapisujemy ciśnienie skurczowe
                    Pomiar.objects.create(
                        pacjentka=pacjentka,
                        typ='cisnienie_s',
                        wartosc=skurczowe,
                        data_pomiaru=data_pomiaru
                    )
                    # Zapisujemy ciśnienie rozkurczowe
                    Pomiar.objects.create(
                        pacjentka=pacjentka,
                        typ='cisnienie_r',
                        wartosc=rozkurczowe,
                        data_pomiaru=data_pomiaru
                    )
                else:
                    # Pozostałe pomiary zapisujemy normalnie
                    pomiar = f.save(commit=False)
                    pomiar.pacjentka = pacjentka
                    pomiar.save()

                return redirect('pomiary')

        elif akcja == 'dodaj_samopoczucie':
            f = FormularzSamopoczucia(request.POST)
            if f.is_valid():
                # Zapisujemy samopoczucie jako specjalny typ pomiaru
                samopoczucie = f.save(commit=False)
                samopoczucie.pacjentka = pacjentka
                # Typ ustawiamy na specjalną wartość
                samopoczucie.typ = 'samopoczucie'
                samopoczucie.wartosc = f.cleaned_data['samopoczucie']
                samopoczucie.save()
                return redirect('pomiary')

    def pobierz_dane(typ):
        rekordy = Pomiar.objects.filter(
            pacjentka=pacjentka,
            typ=typ
        ).order_by('data_pomiaru').values_list('data_pomiaru', 'wartosc')
        return {
            'etykiety': [r[0].strftime('%d.%m %H:%M') for r in rekordy],
            'wartosci': [r[1] for r in rekordy],
        }

    return render(request, 'monitor/pomiary.html', {
        'f_pomiar': FormularzPomiaru(),
        'f_samopoczucie': FormularzSamopoczucia(),
        'historia_pomiarow': pacjentka.pomiary.exclude(
            typ__in=['samopoczucie', 'cisnienie_s', 'cisnienie_r']
        ),
        # Ciśnienia grupujemy osobno
        'historia_cisnienia': pacjentka.pomiary.filter(
            typ='cisnienie_s'
        ).order_by('-data_pomiaru'),
        'historia_cisnienia_r': pacjentka.pomiary.filter(
            typ='cisnienie_r'
        ).order_by('-data_pomiaru'),
        'historia_samopoczucia': pacjentka.pomiary.filter(
            typ='samopoczucie'
        ).order_by('-data_pomiaru')[:10],
        'dane_glukoza': pobierz_dane('glukoza'),
        'dane_cisnienie_s': pobierz_dane('cisnienie_s'),
        'dane_cisnienie_r': pobierz_dane('cisnienie_r'),
    })



# PANEL LEKARZA
@tylko_lekarz
def panel_lekarza(request):
    if request.method == 'POST':
        akcja = request.POST.get('akcja')

        # Lekarz dodaje pacjentkę po PESEL
        if akcja == 'dodaj_pacjentke':
            f = FormularzDodajPacjentkePesel(request.POST)
            if f.is_valid():
                pesel = f.cleaned_data['pesel']
                try:
                    # Szukamy pacjentki z tym PESELem w bazie
                    pacjentka = Pacjentka.objects.get(pesel=pesel)
                    # get_or_create = dodaj relację jeśli nie istnieje
                    _, utworzono = PacjentkaLekarza.objects.get_or_create(
                        lekarz=request.user,
                        pacjentka=pacjentka
                    )
                    if not utworzono:
                        # Pacjentka już jest na liście
                        komunikat = 'Ta pacjentka jest już na Twojej liście!'
                    else:
                        komunikat = f'Pacjentka {pacjentka} została dodana!'
                except Pacjentka.DoesNotExist:
                    # Nie znaleziono pacjentki z tym PESELem
                    komunikat = 'Nie znaleziono pacjentki z tym numerem PESEL!'
                    f.add_error('pesel', komunikat)

                return render(request, 'monitor/panel_lekarza.html', {
                    # Pokazujemy tylko pacjentki tego lekarza
                    'pacjentki': PacjentkaLekarza.objects.filter(
                        lekarz=request.user
                    ),
                    'f_dodaj_pacjentke': f,
                    'f_recepta': FormularzRecepty(),
                    'f_wizyta': FormularzWizytyLekarza(),
                    'wszystkie_wizyty': WizytaLekarska.objects.filter(
                        lekarz=request.user
                    ).order_by('data_wizyty'),
                    'komunikat': komunikat if 'komunikat' in dir() else None,
                })

        elif akcja == 'wypisz_recepte':
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

    # GET – pobierz tylko pacjentki tego lekarza
    moje_pacjentki = PacjentkaLekarza.objects.filter(lekarz=request.user)

    return render(request, 'monitor/panel_lekarza.html', {
        'pacjentki': moje_pacjentki,
        'f_dodaj_pacjentke': FormularzDodajPacjentkePesel(),
        'f_recepta': FormularzRecepty(),
        'f_wizyta': FormularzWizytyLekarza(),
        'wszystkie_wizyty': WizytaLekarska.objects.filter(
            lekarz=request.user
        ).order_by('data_wizyty'),
    })



# SZCZEGÓŁY PACJENTKI – dla lekarza
@tylko_lekarz
def szczegoly_pacjentki(request, pacjentka_id):
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
                f.save_m2m()
                recepta.pacjentki.add(pacjentka)
                return redirect('szczegoly_pacjentki',
                                pacjentka_id=pacjentka_id)
               

        elif akcja == 'umow_wizyte':
            f = FormularzWizytyLekarza(request.POST)
            if f.is_valid():
                wizyta = f.save(commit=False)
                wizyta.lekarz = request.user
                wizyta.pacjentka = pacjentka
                wizyta.save()
                return redirect('szczegoly_pacjentki', pacjentka_id=pacjentka_id)

    # Dane do wykresów – tak samo jak u pacjentki
    def pobierz_dane(typ):
        rekordy = Pomiar.objects.filter(
            pacjentka=pacjentka,
            typ=typ
        ).order_by('data_pomiaru').values_list('data_pomiaru', 'wartosc')
        return {
            'etykiety': [r[0].strftime('%d.%m %H:%M') for r in rekordy],
            'wartosci': [r[1] for r in rekordy],
        }

    # Formularze z pacjentką już wypełnioną
    f_recepta = FormularzReceptyDlaPacjentki()
    f_wizyta = FormularzWizytyLekarza(
        initial={'pacjentka': pacjentka}
    )

    return render(request, 'monitor/szczegoly_pacjentki.html', {
        'pacjentka': pacjentka,
        # Pomiary bez ciśnień i samopoczucia
        'pomiary': pacjentka.pomiary.exclude(
            typ__in=['samopoczucie', 'cisnienie_s', 'cisnienie_r']
        ),
        # Ciśnienia osobno do połączenia w tabeli
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
        'f_recepta': f_recepta,
        'f_wizyta': f_wizyta,
        'dane_glukoza': pobierz_dane('glukoza'),
        'dane_cisnienie_s': pobierz_dane('cisnienie_s'),
        'dane_cisnienie_r': pobierz_dane('cisnienie_r'),
        
    })

