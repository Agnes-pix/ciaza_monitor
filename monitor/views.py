from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
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
    FormularzFiltrowaniaPomiarow,
    FormularzFiltrowaniaPacjentek,
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
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas



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

    # Pomiary "proste" (glukoza, tetno) - bez samopoczucia i ciśnienia
    pomiary_proste = pacjentka.pomiary.exclude(
        typ__in=['samopoczucie', 'cisnienie_s', 'cisnienie_r']
    ).order_by('-data_pomiaru')[:5]

    cisnienia_s_qs = pacjentka.pomiary.filter(
        typ='cisnienie_s'
    ).order_by('-data_pomiaru')[:5]
    cisnienia_r_qs = pacjentka.pomiary.filter(typ='cisnienie_r')

    rozkurczowe_po_dacie = {r.data_pomiaru: r.wartosc for r in cisnienia_r_qs}

    wiersze = []

    for p in pomiary_proste:
        wiersze.append({
            'jest_cisnieniem': False,
            'rodzaj': p.get_typ_nazwa(),
            'wartosc': p.wartosc,
            'data_pomiaru': p.data_pomiaru,
        })

    for s in cisnienia_s_qs:
        rozkurczowe = rozkurczowe_po_dacie.get(s.data_pomiaru)
        if rozkurczowe is not None:
            wiersze.append({
                'jest_cisnieniem': True,
                'rodzaj': 'Ciśnienie krwi',
                'skurczowe': s.wartosc,
                'rozkurczowe': rozkurczowe,
                'data_pomiaru': s.data_pomiaru,
            })

    wiersze.sort(key=lambda w: w['data_pomiaru'], reverse=True)
    ostatnie_pomiary = wiersze[:3]

    # ── Recepty: podział na "w realizacji" i "zrealizowane" + paginacja po 2 ──
    recepty_w_realizacji_qs = pacjentka.recepty.filter(
        do_zrealizowania=True
    ).order_by('-data_wypisania')
    recepty_zrealizowane_qs = pacjentka.recepty.filter(
        do_zrealizowania=False
    ).order_by('-data_realizacji')

    RECEPT_NA_STRONE = 2

    paginator_recepty_realizacja = Paginator(
        recepty_w_realizacji_qs, RECEPT_NA_STRONE
    )
    numer_strony_realizacja = request.GET.get('strona_recept_realizacja', 1)
    try:
        recepty_w_realizacji = paginator_recepty_realizacja.page(
            numer_strony_realizacja
        )
    except (EmptyPage, PageNotAnInteger):
        recepty_w_realizacji = paginator_recepty_realizacja.page(1)

    paginator_recepty_zrealizowane = Paginator(
        recepty_zrealizowane_qs, RECEPT_NA_STRONE
    )
    numer_strony_zrealizowane = request.GET.get(
        'strona_recept_zrealizowane', 1
    )
    try:
        recepty_zrealizowane = paginator_recepty_zrealizowane.page(
            numer_strony_zrealizowane
        )
    except (EmptyPage, PageNotAnInteger):
        recepty_zrealizowane = paginator_recepty_zrealizowane.page(1)

    return render(request, 'monitor/dashboard.html', {
        'pacjentka': pacjentka,
        'dni_do_porodu': dni_do_porodu,
        'wizyty': WizytaLekarska.objects.filter(
            pacjentka=pacjentka
        ).order_by('data_wizyty'),
        'ostatnie_pomiary': ostatnie_pomiary,
        'recepty_w_realizacji': recepty_w_realizacji,
        'paginator_recepty_realizacja': paginator_recepty_realizacja,
        'recepty_zrealizowane': recepty_zrealizowane,
        'paginator_recepty_zrealizowane': paginator_recepty_zrealizowane,
    })

# ================================================================
# WIDOK – Pomiary pacjentki
# Dostępny tylko dla zalogowanych pacjentek
# GET: pokazuje formularz i historię pomiarów
# POST: zapisuje nowy pomiar lub samopoczucie
#
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

    # ── Filtrowanie ───────────────────────────────────────────────
    f_filtr = FormularzFiltrowaniaPomiarow(request.GET or None)

    typ_filtr = None
    data_od = None
    data_do = None
    if f_filtr.is_valid():
        typ_filtr = f_filtr.cleaned_data.get('typ')
        data_od = f_filtr.cleaned_data.get('data_od')
        data_do = f_filtr.cleaned_data.get('data_do')

    # Pomiary "proste" (glukoza, tetno) - bez samopoczucia i bez ciśnienia
    pomiary_proste = pacjentka.pomiary.exclude(
        typ__in=['samopoczucie', 'cisnienie_s', 'cisnienie_r']
    )
    if typ_filtr and typ_filtr != 'cisnienie':
        pomiary_proste = pomiary_proste.filter(typ=typ_filtr)
    elif typ_filtr == 'cisnienie':
        pomiary_proste = pomiary_proste.none()
    if data_od:
        pomiary_proste = pomiary_proste.filter(data_pomiaru__date__gte=data_od)
    if data_do:
        pomiary_proste = pomiary_proste.filter(data_pomiaru__date__lte=data_do)

    # Ciśnienie - osobne querysety s/r, łączone w pary po dacie
    cisnienia_s_qs = pacjentka.pomiary.filter(typ='cisnienie_s')
    cisnienia_r_qs = pacjentka.pomiary.filter(typ='cisnienie_r')
    if typ_filtr and typ_filtr != 'cisnienie':
        cisnienia_s_qs = cisnienia_s_qs.none()
        cisnienia_r_qs = cisnienia_r_qs.none()
    if data_od:
        cisnienia_s_qs = cisnienia_s_qs.filter(data_pomiaru__date__gte=data_od)
        cisnienia_r_qs = cisnienia_r_qs.filter(data_pomiaru__date__gte=data_od)
    if data_do:
        cisnienia_s_qs = cisnienia_s_qs.filter(data_pomiaru__date__lte=data_do)
        cisnienia_r_qs = cisnienia_r_qs.filter(data_pomiaru__date__lte=data_do)

    # Słownik rozkurczowych po dacie pomiaru - O(n) parowanie zamiast O(n^2)
    rozkurczowe_po_dacie = {r.data_pomiaru: r.wartosc for r in cisnienia_r_qs}

    # ── Budujemy jedną wspólną listę "wierszy" do wyświetlenia ─────
    wiersze = []

    for p in pomiary_proste:
        wiersze.append({
            'jest_cisnieniem': False,
            'rodzaj': p.get_typ_nazwa(),
            'wartosc': p.wartosc,
            'data_pomiaru': p.data_pomiaru,
        })

    for s in cisnienia_s_qs:
        rozkurczowe = rozkurczowe_po_dacie.get(s.data_pomiaru)
        if rozkurczowe is not None:
            wiersze.append({
                'jest_cisnieniem': True,
                'rodzaj': 'Ciśnienie krwi',
                'skurczowe': s.wartosc,
                'rozkurczowe': rozkurczowe,
                'data_pomiaru': s.data_pomiaru,
            })

    # Sortowanie chronologiczne - najnowsze na górze
    wiersze.sort(key=lambda w: w['data_pomiaru'], reverse=True)

    # ── Paginacja (na już scalonej i posortowanej liście) ──────────
    WYNIKOW_NA_STRONE_DOMYSLNIE = 6
    try:
        wynikow_na_strone = int(request.GET.get('na_strone',
                                                 WYNIKOW_NA_STRONE_DOMYSLNIE))
        if wynikow_na_strone not in [6, 10, 20, 50]:
            wynikow_na_strone = WYNIKOW_NA_STRONE_DOMYSLNIE
    except (ValueError, TypeError):
        wynikow_na_strone = WYNIKOW_NA_STRONE_DOMYSLNIE

    paginator = Paginator(wiersze, wynikow_na_strone)
    numer_strony = request.GET.get('strona', 1)
    try:
        strona_wynikow = paginator.page(numer_strony)
    except (EmptyPage, PageNotAnInteger):
        strona_wynikow = paginator.page(1)

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
        'f_filtr': f_filtr,
        'wiersze': strona_wynikow,
        'paginator': paginator,
        'wynikow_na_strone': wynikow_na_strone,
        'historia_samopoczucia': pacjentka.pomiary.filter(
            typ='samopoczucie'
        ).order_by('-data_pomiaru')[:10],
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
# WIDOK – Generowanie PDF recepty
# Dostępny dla pacjentki (jej własna recepta) i lekarza (jego recepta)
# Zwraca prosty dokument PDF z danymi recepty
# ================================================================
def recepta_pdf(request, recepta_id):
    recepta = get_object_or_404(Recepta, id=recepta_id)

    # Sprawdzamy dostęp: pacjentka widzi tylko swoje recepty,
    # lekarz tylko te które sam wypisał (lub ma pacjentkę na liście)
    if hasattr(request.user, 'pacjentka'):
        if recepta.pacjentka != request.user.pacjentka:
            return HttpResponse('Brak dostępu', status=403)
    elif hasattr(request.user, 'lekarz'):
        ma_dostep = PacjentkaLekarza.objects.filter(
            lekarz=request.user.lekarz,
            pacjentka=recepta.pacjentka
        ).exists()
        if not ma_dostep:
            return HttpResponse('Brak dostępu', status=403)
    else:
        return HttpResponse('Brak dostępu', status=403)

    bufor = io.BytesIO()
    p = canvas.Canvas(bufor, pagesize=A4)
    szerokosc, wysokosc = A4

    y = wysokosc - 3 * cm

    p.setFont('Helvetica-Bold', 18)
    p.drawString(2 * cm, y, 'Recepta')
    y -= 1 * cm

    p.setFont('Helvetica', 10)
    p.drawString(2 * cm, y, f"Kod recepty: {recepta.kod_recepty or '—'}")
    y -= 0.6 * cm
    p.drawString(2 * cm, y,
                 f"Data wypisania: {recepta.data_wypisania.strftime('%d.%m.%Y')}")
    y -= 1 * cm

    p.line(2 * cm, y, szerokosc - 2 * cm, y)
    y -= 1 * cm

    p.setFont('Helvetica-Bold', 12)
    p.drawString(2 * cm, y, 'Pacjentka')
    y -= 0.6 * cm
    p.setFont('Helvetica', 11)
    p.drawString(2 * cm, y, str(recepta.pacjentka))
    y -= 0.5 * cm
    p.drawString(2 * cm, y, f"PESEL: {recepta.pacjentka.pesel}")
    y -= 1 * cm

    p.setFont('Helvetica-Bold', 12)
    p.drawString(2 * cm, y, 'Lekarz')
    y -= 0.6 * cm
    p.setFont('Helvetica', 11)
    if recepta.lekarz:
        p.drawString(2 * cm, y, str(recepta.lekarz))
        y -= 0.5 * cm
        p.drawString(2 * cm, y, f"PWZ: {recepta.lekarz.pwz}")
    else:
        p.drawString(2 * cm, y, '—')
    y -= 1.2 * cm

    p.line(2 * cm, y, szerokosc - 2 * cm, y)
    y -= 1 * cm

    p.setFont('Helvetica-Bold', 14)
    p.drawString(2 * cm, y, recepta.nazwa_leku)
    y -= 0.7 * cm
    p.setFont('Helvetica', 11)
    p.drawString(2 * cm, y, f"Dawkowanie: {recepta.dawkowanie}")
    y -= 1 * cm

    if recepta.uwagi:
        p.setFont('Helvetica-Bold', 11)
        p.drawString(2 * cm, y, 'Uwagi:')
        y -= 0.6 * cm
        p.setFont('Helvetica', 10)
        for linia in recepta.uwagi.split('\n'):
            p.drawString(2 * cm, y, linia)
            y -= 0.5 * cm

    p.showPage()
    p.save()
    bufor.seek(0)

    odpowiedz = HttpResponse(bufor.getvalue(), content_type='application/pdf')
    nazwa = f"recepta_{recepta.kod_recepty or recepta.id}.pdf"
    if request.GET.get('podglad') == '1':
        odpowiedz['Content-Disposition'] = f'inline; filename="{nazwa}"'
    else:
        odpowiedz['Content-Disposition'] = f'attachment; filename="{nazwa}"'
    return odpowiedz

# ================================================================
# WIDOK – Oznaczanie recepty jako zrealizowanej
# Dostępny dla pacjentki i lekarza (obaj mogą kliknąć "Zrealizowano")
# Ustawia do_zrealizowania=False i zapisuje datę realizacji
# ================================================================
def recepta_zrealizowano(request, recepta_id):
    recepta = get_object_or_404(Recepta, id=recepta_id)

    if hasattr(request.user, 'pacjentka'):
        if recepta.pacjentka != request.user.pacjentka:
            return HttpResponse('Brak dostępu', status=403)
        powrot = 'pomiary'
        powrot_kwargs = {}
    elif hasattr(request.user, 'lekarz'):
        ma_dostep = PacjentkaLekarza.objects.filter(
            lekarz=request.user.lekarz,
            pacjentka=recepta.pacjentka
        ).exists()
        if not ma_dostep:
            return HttpResponse('Brak dostępu', status=403)
        powrot = 'szczegoly_pacjentki'
        powrot_kwargs = {'pacjentka_id': recepta.pacjentka.id}
    else:
        return HttpResponse('Brak dostępu', status=403)

    if request.method == 'POST':
        recepta.do_zrealizowania = False
        recepta.data_realizacji = timezone.now()
        recepta.save()

    return redirect(powrot, **powrot_kwargs)


# ================================================================
# WIDOK – Usuwanie recepty przez lekarza
# Dostępny tylko dla lekarza który wypisał/ma dostęp do tej recepty
# Usuwa natychmiast, bez potwierdzenia
# ================================================================
def recepta_usun(request, recepta_id):
    recepta = get_object_or_404(Recepta, id=recepta_id)

    if not hasattr(request.user, 'lekarz'):
        return HttpResponse('Brak dostępu', status=403)

    ma_dostep = PacjentkaLekarza.objects.filter(
        lekarz=request.user.lekarz,
        pacjentka=recepta.pacjentka
    ).exists()
    if not ma_dostep:
        return HttpResponse('Brak dostępu', status=403)

    pacjentka_id = recepta.pacjentka.id

    if request.method == 'POST':
        recepta.delete()

    return redirect('szczegoly_pacjentki', pacjentka_id=pacjentka_id)

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


# # ================================================================
# # WIDOK – Szczegóły wgranego pliku PDF
# # Pokazuje tekst wyciągnięty z pliku PDF
# # ================================================================
# @tylko_pacjentka
# def szczegoly_pdf(request, plik_id):
#     pacjentka = request.user.pacjentka
#     # get_object_or_404 sprawdza że plik należy do tej pacjentki
#     plik = get_object_or_404(PlikBadan, id=plik_id, pacjentka=pacjentka)
#     return render(request, 'monitor/szczegoly_pdf.html', {'plik': plik})
# ================================================================
# WIDOK – Panel lekarza
# Dostępny tylko dla zalogowanych lekarzy
# GET: pokazuje listę swoich pacjentek
# POST: obsługuje dodanie pacjentki po PESEL
# ================================================================
@tylko_lekarz
def panel_lekarza(request):
    komunikat = None
    f_dodaj = FormularzDodajPacjentkePesel()

    if request.method == 'POST':
        akcja = request.POST.get('akcja')

        if akcja == 'dodaj_pacjentke':
            f_dodaj = FormularzDodajPacjentkePesel(request.POST)
            if f_dodaj.is_valid():
                pesel = f_dodaj.cleaned_data['pesel']
                try:
                    pacjentka = Pacjentka.objects.get(pesel=pesel)
                    _, utworzono = PacjentkaLekarza.objects.get_or_create(
                        lekarz=request.user.lekarz,
                        pacjentka=pacjentka
                    )
                    komunikat = (
                        f'Pacjentka {pacjentka} została dodana!'
                        if utworzono
                        else 'Ta pacjentka jest już na Twojej liście!'
                    )
                except Pacjentka.DoesNotExist:
                    f_dodaj.add_error('pesel',
                                'Nie znaleziono pacjentki z tym numerem PESEL!')

    # ── Filtrowanie ───────────────────────────────────────────────
    f_filtr = FormularzFiltrowaniaPacjentek(request.GET or None)

    pacjentki_qs = PacjentkaLekarza.objects.filter(
        lekarz=request.user.lekarz
    ).select_related('pacjentka__uzytkownik')

    if f_filtr.is_valid():
        szukaj = f_filtr.cleaned_data.get('szukaj')
        porod_od = f_filtr.cleaned_data.get('porod_od')
        porod_do = f_filtr.cleaned_data.get('porod_do')

        if szukaj:
            pacjentki_qs = pacjentki_qs.filter(
                Q(pacjentka__uzytkownik__first_name__icontains=szukaj) |
                Q(pacjentka__uzytkownik__last_name__icontains=szukaj) |
                Q(pacjentka__pesel__icontains=szukaj)
            ).distinct()
        if porod_od:
            pacjentki_qs = pacjentki_qs.filter(
                pacjentka__przewidywana_data_porodu__gte=porod_od
            )
        if porod_do:
            pacjentki_qs = pacjentki_qs.filter(
                pacjentka__przewidywana_data_porodu__lte=porod_do
            )

    # ── Paginacja ─────────────────────────────────────────────────
    WYNIKOW_NA_STRONE_DOMYSLNIE = 10
    try:
        wynikow_na_strone = int(request.GET.get('na_strone',
                                                 WYNIKOW_NA_STRONE_DOMYSLNIE))
        if wynikow_na_strone not in [5, 10, 20, 50]:
            wynikow_na_strone = WYNIKOW_NA_STRONE_DOMYSLNIE
    except (ValueError, TypeError):
        wynikow_na_strone = WYNIKOW_NA_STRONE_DOMYSLNIE

    paginator = Paginator(pacjentki_qs, wynikow_na_strone)
    numer_strony = request.GET.get('strona', 1)
    try:
        strona = paginator.page(numer_strony)
    except (EmptyPage, PageNotAnInteger):
        strona = paginator.page(1)

    return render(request, 'monitor/panel_lekarza.html', {
        'pacjentki': strona,
        'paginator': paginator,
        'wynikow_na_strone': wynikow_na_strone,
        'f_dodaj_pacjentke': f_dodaj,
        'f_filtr': f_filtr,
        'komunikat': komunikat,
        'liczba_wszystkich': pacjentki_qs.count(),
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
        lekarz=request.user.lekarz,
        pacjentka__id=pacjentka_id
    )
    pacjentka = relacja.pacjentka

    if request.method == 'POST':
        akcja = request.POST.get('akcja')

        if akcja == 'wypisz_recepte':
            f = FormularzReceptyDlaPacjentki(request.POST)
            if f.is_valid():
                recepta = f.save(commit=False)
                recepta.lekarz = request.user.lekarz
                recepta.pacjentka = pacjentka
                recepta.save()
                return redirect('szczegoly_pacjentki',
                                pacjentka_id=pacjentka_id)

        elif akcja == 'umow_wizyte':
            f = FormularzWizytyDlaPacjentki(request.POST)
            if f.is_valid():
                wizyta = f.save(commit=False)
                wizyta.lekarz = request.user.lekarz
                wizyta.pacjentka = pacjentka
                wizyta.save()
                return redirect('szczegoly_pacjentki',
                                pacjentka_id=pacjentka_id)

    # ── Filtrowanie pomiarów ──────────────────────────────────────
    f_filtr = FormularzFiltrowaniaPomiarow(request.GET or None)

    typ_filtr = None
    data_od = None
    data_do = None
    if f_filtr.is_valid():
        typ_filtr = f_filtr.cleaned_data.get('typ')
        data_od = f_filtr.cleaned_data.get('data_od')
        data_do = f_filtr.cleaned_data.get('data_do')

    # Pomiary "proste" (glukoza, tetno) - bez samopoczucia i bez ciśnienia
    pomiary_proste = pacjentka.pomiary.exclude(
        typ__in=['samopoczucie', 'cisnienie_s', 'cisnienie_r']
    )
    if typ_filtr and typ_filtr != 'cisnienie':
        pomiary_proste = pomiary_proste.filter(typ=typ_filtr)
    elif typ_filtr == 'cisnienie':
        pomiary_proste = pomiary_proste.none()
    if data_od:
        pomiary_proste = pomiary_proste.filter(data_pomiaru__date__gte=data_od)
    if data_do:
        pomiary_proste = pomiary_proste.filter(data_pomiaru__date__lte=data_do)

    # Ciśnienie - osobne querysety s/r, łączone w pary po dacie
    cisnienia_s_qs = pacjentka.pomiary.filter(typ='cisnienie_s')
    cisnienia_r_qs = pacjentka.pomiary.filter(typ='cisnienie_r')
    if typ_filtr and typ_filtr != 'cisnienie':
        cisnienia_s_qs = cisnienia_s_qs.none()
        cisnienia_r_qs = cisnienia_r_qs.none()
    if data_od:
        cisnienia_s_qs = cisnienia_s_qs.filter(data_pomiaru__date__gte=data_od)
        cisnienia_r_qs = cisnienia_r_qs.filter(data_pomiaru__date__gte=data_od)
    if data_do:
        cisnienia_s_qs = cisnienia_s_qs.filter(data_pomiaru__date__lte=data_do)
        cisnienia_r_qs = cisnienia_r_qs.filter(data_pomiaru__date__lte=data_do)

    # Słownik rozkurczowych po dacie pomiaru - O(n) parowanie zamiast O(n^2)
    rozkurczowe_po_dacie = {r.data_pomiaru: r.wartosc for r in cisnienia_r_qs}

    # ── Budujemy jedną wspólną listę "wierszy" do wyświetlenia ─────
    wiersze = []

    for p in pomiary_proste:
        wiersze.append({
            'jest_cisnieniem': False,
            'rodzaj': p.get_typ_nazwa(),
            'wartosc': p.wartosc,
            'data_pomiaru': p.data_pomiaru,
        })

    for s in cisnienia_s_qs:
        rozkurczowe = rozkurczowe_po_dacie.get(s.data_pomiaru)
        if rozkurczowe is not None:
            wiersze.append({
                'jest_cisnieniem': True,
                'rodzaj': 'Ciśnienie krwi',
                'skurczowe': s.wartosc,
                'rozkurczowe': rozkurczowe,
                'data_pomiaru': s.data_pomiaru,
            })

    # Sortowanie chronologiczne - najnowsze na górze
    wiersze.sort(key=lambda w: w['data_pomiaru'], reverse=True)

    # ── Paginacja (na już scalonej i posortowanej liście) ──────────
    WYNIKOW_NA_STRONE_DOMYSLNIE = 6
    try:
        wynikow_na_strone = int(request.GET.get('na_strone',
                                                 WYNIKOW_NA_STRONE_DOMYSLNIE))
        if wynikow_na_strone not in [6, 10, 20, 50]:
            wynikow_na_strone = WYNIKOW_NA_STRONE_DOMYSLNIE
    except (ValueError, TypeError):
        wynikow_na_strone = WYNIKOW_NA_STRONE_DOMYSLNIE

    paginator = Paginator(wiersze, wynikow_na_strone)
    numer_strony = request.GET.get('strona', 1)
    try:
        strona_wynikow = paginator.page(numer_strony)
    except (EmptyPage, PageNotAnInteger):
        strona_wynikow = paginator.page(1)

    # Funkcja pomocnicza do pobierania danych dla wykresów
    def pobierz_dane(typ):
        rekordy = Pomiar.objects.filter(
            pacjentka=pacjentka, typ=typ
        ).order_by('data_pomiaru').values_list('data_pomiaru', 'wartosc')
        return {
            'etykiety': [r[0].strftime('%d.%m %H:%M') for r in rekordy],
            'wartosci': [r[1] for r in rekordy],
        }

# ── Recepty: podział na "w realizacji" i "zrealizowane" + paginacja po 2 ──
    recepty_w_realizacji_qs = pacjentka.recepty.filter(
        do_zrealizowania=True
    ).order_by('-data_wypisania')
    recepty_zrealizowane_qs = pacjentka.recepty.filter(
        do_zrealizowania=False
    ).order_by('-data_realizacji')

    RECEPT_NA_STRONE = 2

    paginator_recepty_realizacja = Paginator(
        recepty_w_realizacji_qs, RECEPT_NA_STRONE
    )
    numer_strony_realizacja = request.GET.get('strona_recept_realizacja', 1)
    try:
        recepty_w_realizacji = paginator_recepty_realizacja.page(
            numer_strony_realizacja
        )
    except (EmptyPage, PageNotAnInteger):
        recepty_w_realizacji = paginator_recepty_realizacja.page(1)

    paginator_recepty_zrealizowane = Paginator(
        recepty_zrealizowane_qs, RECEPT_NA_STRONE
    )
    numer_strony_zrealizowane = request.GET.get(
        'strona_recept_zrealizowane', 1
    )
    try:
        recepty_zrealizowane = paginator_recepty_zrealizowane.page(
            numer_strony_zrealizowane
        )
    except (EmptyPage, PageNotAnInteger):
        recepty_zrealizowane = paginator_recepty_zrealizowane.page(1)

    return render(request, 'monitor/szczegoly_pacjentki.html', {
        'pacjentka': pacjentka,
        'f_recepta': FormularzReceptyDlaPacjentki(),
        'f_wizyta': FormularzWizytyDlaPacjentki(),
        'f_filtr': f_filtr,
        'wiersze': strona_wynikow,
        'paginator': paginator,
        'wynikow_na_strone': wynikow_na_strone,
        'historia_samopoczucia': pacjentka.pomiary.filter(
            typ='samopoczucie'
        ).order_by('-data_pomiaru'),
        'wizyty': pacjentka.wizyty.all(),
        'pliki_badan': pacjentka.pliki_badan.all(),
        'dane_glukoza': pobierz_dane('glukoza'),
        'dane_cisnienie_s': pobierz_dane('cisnienie_s'),
        'dane_cisnienie_r': pobierz_dane('cisnienie_r'),
        'recepty_w_realizacji': recepty_w_realizacji,
        'paginator_recepty_realizacja': paginator_recepty_realizacja,
        'recepty_zrealizowane': recepty_zrealizowane,
        'paginator_recepty_zrealizowane': paginator_recepty_zrealizowane,
    })