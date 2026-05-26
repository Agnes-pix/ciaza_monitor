from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from .decorators import tylko_pacjentka, tylko_lekarz
from .models import Pacjentka, Pomiar, WizytaLekarska, Recepta, PacjentkaLekarza, PlikBadan
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
    FormularzPlikuBadan,
)
from django.http import HttpResponse
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import matplotlib
matplotlib.use('Agg')  # tryb bez okna GUI – wymagany na serwerze
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pypdf import PdfReader


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

@tylko_pacjentka
def eksport_xlsx(request):
    pacjentka = request.user.pacjentka

    # Tworzymy skoroszyt Excel w pamięci
    wb = openpyxl.Workbook()

    # Styl nagłówków
    styl_naglowek = Font(bold=True, color='FFFFFF')
    wypelnienie = PatternFill(
        start_color='880E4F',
        end_color='880E4F',
        fill_type='solid'
    )
    wyrownanie = Alignment(horizontal='center')

    # ── Arkusz 1: Pomiary ──────────────────────
    ws_pomiary = wb.active
    ws_pomiary.title = 'Pomiary'

    naglowki = ['Lp.', 'Rodzaj pomiaru', 'Wartość', 'Data i godzina']
    for kolumna, tekst in enumerate(naglowki, start=1):
        komorka = ws_pomiary.cell(row=1, column=kolumna, value=tekst)
        komorka.font = styl_naglowek
        komorka.fill = wypelnienie
        komorka.alignment = wyrownanie

    ws_pomiary.column_dimensions['A'].width = 6
    ws_pomiary.column_dimensions['B'].width = 30
    ws_pomiary.column_dimensions['C'].width = 15
    ws_pomiary.column_dimensions['D'].width = 20

    # Wypełniamy pomiarami (bez ciśnień i samopoczucia)
    pomiary = pacjentka.pomiary.exclude(
        typ__in=['samopoczucie', 'cisnienie_s', 'cisnienie_r']
    )
    for i, pomiar in enumerate(pomiary, start=1):
        ws_pomiary.cell(row=i+1, column=1, value=i)
        ws_pomiary.cell(row=i+1, column=2,
                        value=pomiar.get_typ_nazwa())
        ws_pomiary.cell(row=i+1, column=3, value=pomiar.wartosc)
        ws_pomiary.cell(row=i+1, column=4,
                        value=pomiar.data_pomiaru.strftime('%d.%m.%Y %H:%M'))

    # Ciśnienia jako pary 120/80
    cisnienia_s = list(pacjentka.pomiary.filter(
        typ='cisnienie_s').order_by('-data_pomiaru'))
    cisnienia_r = list(pacjentka.pomiary.filter(
        typ='cisnienie_r').order_by('-data_pomiaru'))

    wiersz = len(pomiary) + 2
    for s, r in zip(cisnienia_s, cisnienia_r):
        ws_pomiary.cell(row=wiersz, column=1, value=wiersz-1)
        ws_pomiary.cell(row=wiersz, column=2, value='Ciśnienie krwi (mmHg)')
        ws_pomiary.cell(row=wiersz, column=3,
                        value=f"{int(s.wartosc)}/{int(r.wartosc)}")
        ws_pomiary.cell(row=wiersz, column=4,
                        value=s.data_pomiaru.strftime('%d.%m.%Y %H:%M'))
        wiersz += 1

    # ── Arkusz 2: Wizyty ───────────────────────
    ws_wizyty = wb.create_sheet(title='Wizyty lekarskie')
    naglowki_wizyty = ['Lp.', 'Specjalizacja', 'Miejsce',
                        'Data wizyty', 'Status']
    for kolumna, tekst in enumerate(naglowki_wizyty, start=1):
        komorka = ws_wizyty.cell(row=1, column=kolumna, value=tekst)
        komorka.font = styl_naglowek
        komorka.fill = wypelnienie

    for i, wizyta in enumerate(pacjentka.wizyty.all(), start=1):
        ws_wizyty.cell(row=i+1, column=1, value=i)
        ws_wizyty.cell(row=i+1, column=2, value=wizyta.specjalizacja)
        ws_wizyty.cell(row=i+1, column=3, value=wizyta.miejsce)
        ws_wizyty.cell(row=i+1, column=4,
                        value=wizyta.data_wizyty.strftime('%d.%m.%Y %H:%M'))
        ws_wizyty.cell(row=i+1, column=5,
                        value='Odbyta' if wizyta.odbyta else 'Zaplanowana')

    # ── Arkusz 3: Dane pacjentki ───────────────
    ws_info = wb.create_sheet(title='Dane pacjentki')
    info = [
        ('Imię i nazwisko', str(pacjentka)),
        ('PESEL', pacjentka.pesel),
        ('Data urodzenia', str(pacjentka.data_urodzenia)),
        ('Przewidywana data porodu',
         str(pacjentka.przewidywana_data_porodu)),
        ('Data eksportu', timezone.now().strftime('%d.%m.%Y %H:%M')),
    ]
    for wiersz, (klucz, wartosc) in enumerate(info, start=1):
        komorka = ws_info.cell(row=wiersz, column=1, value=klucz)
        komorka.font = Font(bold=True)
        ws_info.cell(row=wiersz, column=2, value=wartosc)

    ws_info.column_dimensions['A'].width = 30
    ws_info.column_dimensions['B'].width = 30

    # Zapisujemy do bufora w pamięci i zwracamy jako plik
    bufor = io.BytesIO()
    wb.save(bufor)
    bufor.seek(0)

    odpowiedz = HttpResponse(
        bufor.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    nazwa = f"pomiary_{pacjentka.pesel}.xlsx"
    odpowiedz['Content-Disposition'] = f'attachment; filename="{nazwa}"'
    return odpowiedz


# ================================================================
# WIDOK – Dynamiczny wykres PNG generowany przez matplotlib
# Dostępny tylko dla zalogowanej pacjentki
# Parametr URL: ?typ=glukoza lub ?typ=cisnienie
# Zwraca obrazek PNG jako odpowiedź HTTP
# ================================================================
@tylko_pacjentka
def wykres_png(request):
    pacjentka = request.user.pacjentka
    typ = request.GET.get('typ', 'glukoza')

    # Konfiguracja dla każdego typu wykresu
    konfiguracja = {
        'glukoza': {
            'tytul': 'Poziom glukozy',
            'kolor': '#E91E8C',
            'jednostka': 'mg/dL',
            'norma_min': 70,
            'norma_max': 140,
        },
        'cisnienie': {
            'tytul': 'Ciśnienie krwi',
            'kolor': '#1976D2',
            'jednostka': 'mmHg',
            'norma_min': None,
            'norma_max': None,
        },
        'tetno': {
            'tytul': 'Tętno',
            'kolor': '#9C27B0',
            'jednostka': 'uderzenia/min',
            'norma_min': 60,
            'norma_max': 100,
        },
    }
    cfg = konfiguracja.get(typ, konfiguracja['glukoza'])

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor('#FAFAFA')
    ax.set_facecolor('#FFFFFF')

    if typ == 'cisnienie':
        # Ciśnienie ma dwie linie
        cisnienia_s = list(pacjentka.pomiary.filter(
            typ='cisnienie_s').order_by('data_pomiaru'))
        cisnienia_r = list(pacjentka.pomiary.filter(
            typ='cisnienie_r').order_by('data_pomiaru'))

        if cisnienia_s and cisnienia_r:
            daty = [p.data_pomiaru for p in cisnienia_s]
            wartosci_s = [p.wartosc for p in cisnienia_s]
            wartosci_r = [p.wartosc for p in cisnienia_r]

            ax.plot(daty, wartosci_s, color='#1976D2', linewidth=2.5,
                    marker='o', markersize=6, label='Skurczowe')
            ax.plot(daty, wartosci_r, color='#FF9800', linewidth=2.5,
                    marker='o', markersize=6, label='Rozkurczowe')
            ax.fill_between(daty, wartosci_s, wartosci_r,
                            alpha=0.1, color='#1976D2')
            ax.legend(loc='upper right')
            ax.xaxis.set_major_formatter(
                mdates.DateFormatter('%d.%m\n%H:%M')
            )
        else:
            ax.text(0.5, 0.5, 'Brak danych do wyświetlenia',
                    transform=ax.transAxes, ha='center', va='center',
                    fontsize=14, color='gray', style='italic')
    else:
        pomiary = pacjentka.pomiary.filter(
            typ=typ
        ).order_by('data_pomiaru')

        if pomiary.exists():
            daty = [p.data_pomiaru for p in pomiary]
            wartosci = [p.wartosc for p in pomiary]

            ax.plot(daty, wartosci, color=cfg['kolor'], linewidth=2.5,
                    marker='o', markersize=6, markerfacecolor='white',
                    markeredgewidth=2)
            ax.fill_between(daty, wartosci, alpha=0.15, color=cfg['kolor'])

            # Linie norm
            if cfg['norma_min']:
                ax.axhline(y=cfg['norma_min'], color='green',
                           linestyle='--', linewidth=1.2, alpha=0.7,
                           label=f"Norma min: {cfg['norma_min']}")
                ax.axhline(y=cfg['norma_max'], color='red',
                           linestyle='--', linewidth=1.2, alpha=0.7,
                           label=f"Norma max: {cfg['norma_max']}")
                ax.legend(loc='upper right')

            ax.xaxis.set_major_formatter(
                mdates.DateFormatter('%d.%m\n%H:%M')
            )
        else:
            ax.text(0.5, 0.5, 'Brak danych do wyświetlenia',
                    transform=ax.transAxes, ha='center', va='center',
                    fontsize=14, color='gray', style='italic')

    ax.set_title(f"{cfg['tytul']} – {pacjentka}",
                 fontsize=13, fontweight='bold', pad=15)
    ax.set_ylabel(cfg['jednostka'], fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()

    # Zapisujemy wykres do bufora PNG
    bufor = io.BytesIO()
    plt.savefig(bufor, format='png', dpi=120, bbox_inches='tight')
    bufor.seek(0)
    plt.close(fig)  # zwalniamy pamięć

    return HttpResponse(bufor.getvalue(), content_type='image/png')


# ================================================================
# WIDOK – Wgrywanie pliku PDF z wynikami badań
# Dostępny tylko dla zalogowanej pacjentki
# GET: pokazuje formularz i listę wgranych plików
# POST: wgrywa plik, wyciąga tekst przez pypdf i zapisuje
# ================================================================
@tylko_pacjentka
def badania_pdf(request):
    pacjentka = request.user.pacjentka

    if request.method == 'POST':
        formularz = FormularzPlikuBadan(request.POST, request.FILES)
        if formularz.is_valid():
            plik_obj = formularz.save(commit=False)
            plik_obj.pacjentka = pacjentka
            plik_obj.nazwa_pliku = request.FILES['plik'].name
            plik_obj.save()
            return redirect('badania_pdf')
    else:
        formularz = FormularzPlikuBadan()

    return render(request, 'monitor/badania_pdf.html', {
        'formularz': formularz,
        'pliki': pacjentka.pliki_badan.all(),
    })


# ================================================================
# WIDOK – Usuwanie wgranego pliku PDF
# Dostępny tylko dla zalogowanej pacjentki
# Sprawdza że plik należy do tej pacjentki przed usunięciem
# ================================================================
@tylko_pacjentka
def usun_pdf(request, plik_id):
    pacjentka = request.user.pacjentka
    plik = get_object_or_404(PlikBadan, id=plik_id, pacjentka=pacjentka)

    if request.method == 'POST':
        # Usuwamy fizyczny plik z dysku
        plik.plik.delete(save=False)
        # Usuwamy rekord z bazy
        plik.delete()
        return redirect('badania_pdf')

    # GET – strona potwierdzenia usunięcia
    return render(request, 'monitor/potwierdz_usuniecie.html', {
        'plik': plik
    })


# ================================================================
# WIDOK – Szczegóły wgranego pliku PDF
# Pokazuje tekst wyciągnięty z pliku PDF
# ================================================================
@tylko_pacjentka
def szczegoly_pdf(request, plik_id):
    pacjentka = request.user.pacjentka
    # get_object_or_404 sprawdza że plik należy do tej pacjentki
    plik = get_object_or_404(PlikBadan, id=plik_id, pacjentka=pacjentka)
    return render(request, 'monitor/szczegoly_pdf.html', {'plik': plik})
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
        'pliki_badan': pacjentka.pliki_badan.all(),
        # Dane do wykresów Chart.js
        'dane_glukoza': pobierz_dane('glukoza'),
        'dane_cisnienie_s': pobierz_dane('cisnienie_s'),
        'dane_cisnienie_r': pobierz_dane('cisnienie_r'),
    })