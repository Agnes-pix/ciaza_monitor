from django.db import models
from django.contrib.auth.models import User


# ================================================================
# MODEL 1 – Pacjentka
# Rozszerza wbudowany model User o dane medyczne
# Relacja: jeden User = jedna Pacjentka (OneToOne)
# ================================================================
class Pacjentka(models.Model):
    uzytkownik = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='pacjentka'
    )
    pesel = models.CharField(max_length=11, unique=True)
    data_urodzenia = models.DateField()
    przewidywana_data_porodu = models.DateField()
    telefon = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.uzytkownik.first_name} {self.uzytkownik.last_name}"

    class Meta:
        verbose_name = 'Pacjentka'
        verbose_name_plural = 'Pacjentki'

# ================================================================
# MODEL 5 – Lekarz
# Rozszerza wbudowany model User o dane zawodowe
# Relacja: jeden User = jeden Lekarz (OneToOne)
# Imię i nazwisko przechowywane są w modelu User
# ================================================================
class Lekarz(models.Model):
    uzytkownik = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        # related_name='profil_lekarza'
    )
    pwz = models.CharField(
        max_length=7,
        unique=True,
        blank=True,
        null=True
    )
    miejsce_pracy = models.CharField(max_length=200, blank=True)
    specjalizacja = models.CharField(max_length=100, blank=True)
    telefon = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"Dr {self.uzytkownik.first_name} {self.uzytkownik.last_name}"

    class Meta:
        verbose_name = 'Lekarz'
        verbose_name_plural = 'Lekarze'

# ================================================================
# MODEL 2 – Pomiar
# Przechowuje wszystkie pomiary pacjentki
# Relacja: wiele Pomiarów należy do jednej Pacjentki (ForeignKey)
#
# Typy pomiarów w bazie:
# - 'glukoza'      – poziom glukozy
# - 'cisnienie_s'  – ciśnienie skurczowe (część pary 120/80)
# - 'cisnienie_r'  – ciśnienie rozkurczowe (część pary 120/80)
# - 'tetno'        – tętno
# - 'samopoczucie' – samopoczucie z notatką
#
# UWAGA: W formularzu ciśnienie wybierane jest jako jedno pole
# w formacie 120/80 i rozdzielane na dwa rekordy w bazie
# ================================================================
class Pomiar(models.Model):
    # Typy wyświetlane użytkownikowi w formularzu dodawania pomiaru
    TYPY_POMIAROW = [
        ('glukoza', 'Poziom glukozy (mg/dL)'),
        ('cisnienie', 'Ciśnienie krwi (mmHg)'),
        ('tetno', 'Tętno (uderzenia/min)'),
    ]

    SAMOPOCZUCIE_WYBORY = [
        (1, '😞 Bardzo złe'),
        (2, '😕 Złe'),
        (3, '😐 Średnie'),
        (4, '🙂 Dobre'),
        (5, '😊 Bardzo dobre'),
    ]

    # Wszystkie typy jakie mogą trafić do bazy – używane przez get_typ_nazwa()
    # Pacjentka wybiera 'cisnienie' w formularzu, ale w bazie zapisywane są
    # dwa osobne rekordy: 'cisnienie_s' i 'cisnienie_r' – dzięki temu
    # wykres może rysować dwie osobne linie na jednym układzie współrzędnych
    WSZYSTKIE_TYPY = {
        'glukoza': 'Poziom glukozy (mg/dL)',
        'cisnienie': 'Ciśnienie krwi (mmHg)',
        'cisnienie_s': 'Ciśnienie skurczowe (mmHg)',
        'cisnienie_r': 'Ciśnienie rozkurczowe (mmHg)',
        'tetno': 'Tętno (uderzenia/min)',
        'samopoczucie': 'Samopoczucie',
    }

    pacjentka = models.ForeignKey(
        Pacjentka,
        on_delete=models.CASCADE,
        related_name='pomiary'
    )
    # typ przechowuje wartości widoczne użytkownikowi (TYPY_POMIAROW)
    # oraz wewnętrzne typy zapisywane przez widok:
    # 'cisnienie_s' – skurczowe (pierwsza liczba z formatu 120/80)
    # 'cisnienie_r' – rozkurczowe (druga liczba z formatu 120/80)
    # 'samopoczucie' – wpis z formularza samopoczucia
    # choices celowo nie jest ustawione – Django nie waliduje pola
    # przy zapisie przez kod, a WSZYSTKIE_TYPY służy do wyświetlania nazw
    typ = models.CharField(
        max_length=20,
        blank=True
    )
    wartosc = models.FloatField()
    data_pomiaru = models.DateTimeField()
    # samopoczucie przechowuje wartość 1-5 z formularza samopoczucia
    # dla wpisów samopoczucia ta sama wartość trafia też do pola wartosc
    # (wymagane przez FloatField) – wartosc nie jest używana dla samopoczucia
    samopoczucie = models.IntegerField(
        choices=SAMOPOCZUCIE_WYBORY,
        null=True,
        blank=True
    )
    notatka = models.TextField(blank=True)

    def __str__(self):
        return f"{self.pacjentka} – {self.typ}: {self.wartosc}"
    
    def get_typ_nazwa(self):
        return self.WSZYSTKIE_TYPY.get(self.typ, self.typ)

    class Meta:
        ordering = ['-data_pomiaru']
        verbose_name = 'Pomiar'
        verbose_name_plural = 'Pomiary'


# ================================================================
# MODEL 3 – WizytaLekarska
# Wizyta umawiania przez lekarza dla konkretnej pacjentki
# Relacja: wiele Wizyt należy do jednej Pacjentki (ForeignKey)
# Relacja: wiele Wizyt należy do jednego Lekarza (ForeignKey)
# ================================================================
class WizytaLekarska(models.Model):
    pacjentka = models.ForeignKey(
        Pacjentka,
        on_delete=models.CASCADE,
        related_name='wizyty'
    )
    lekarz = models.ForeignKey(
        Lekarz,
        on_delete=models.SET_NULL,
        null=True,
        # blank=True,
        related_name='wizyty_lekarza'
    )
    data_wizyty = models.DateTimeField()
    miejsce = models.CharField(max_length=200)
    specjalizacja = models.CharField(max_length=100)
    notatki = models.TextField(blank=True)
    odbyta = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.pacjentka} – {self.specjalizacja}"

    class Meta:
        ordering = ['data_wizyty']
        verbose_name = 'Wizyta lekarska'
        verbose_name_plural = 'Wizyty lekarskie'


# ================================================================
# MODEL 4 – Recepta
# Recepta wypisana przez lekarza dla pacjentki
# Relacja: wiele Recept należy do jednej Pacjentki (ForeignKey)
# Relacja: wiele Recept należy do jednego Lekarza (ForeignKey)
# ================================================================
class Recepta(models.Model):
    lekarz = models.ForeignKey(
        Lekarz,
        on_delete=models.SET_NULL,
        null=True,
        related_name='wypisane_recepty'
    )
    pacjentka = models.ForeignKey(
        Pacjentka,
        on_delete=models.CASCADE,
        related_name='recepty'
    )
    nazwa_leku = models.CharField(max_length=200)
    dawkowanie = models.CharField(max_length=200)
    data_wypisania = models.DateField(auto_now_add=True)
    do_zrealizowania = models.BooleanField(default=True)
    uwagi = models.TextField(blank=True)

    def __str__(self):
        return f"{self.nazwa_leku} – {self.dawkowanie}"

    class Meta:
        verbose_name = 'Recepta'
        verbose_name_plural = 'Recepty'



# ================================================================
# MODEL 6 – PacjentkaLekarza
# Łączy lekarza z jego pacjentkami
# Lekarz dodaje pacjentkę po PESEL – tworzy się ta relacja
# Relacja: wiele do wielu między User (lekarz) a Pacjentka
# ================================================================
class PacjentkaLekarza(models.Model):
    lekarz = models.ForeignKey(
        Lekarz,
        on_delete=models.CASCADE,
        related_name='moje_pacjentki'
    )
    pacjentka = models.ForeignKey(
        Pacjentka,
        on_delete=models.CASCADE,
        related_name='moi_lekarze'
    )
    data_dodania = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['lekarz', 'pacjentka']
        verbose_name = 'Pacjentka lekarza'
        verbose_name_plural = 'Pacjentki lekarza'

    def __str__(self):
        return f"Dr {self.lekarz.uzytkownik.last_name} – {self.pacjentka}"
    

# ================================================================
# MODEL 7 – PlikBadan
# Przechowuje pliki PDF wgrane przez pacjentkę
# Relacja: wiele Plików należy do jednej Pacjentki (ForeignKey)
# ================================================================
class PlikBadan(models.Model):
    pacjentka = models.ForeignKey(
        Pacjentka,
        on_delete=models.CASCADE,
        related_name='pliki_badan'
    )
    # FileField = pole przechowujące ścieżkę do pliku na dysku
    # upload_to = podfolder w MEDIA_ROOT gdzie trafia plik
    plik = models.FileField(upload_to='badania/')
    nazwa_pliku = models.CharField(max_length=255)
    data_wgrania = models.DateTimeField(auto_now_add=True)
    # Tekst wyciągnięty z PDF – zapisujemy żeby nie czytać za każdym razem
    wyciagniety_tekst = models.TextField(blank=True)
    opis = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return f"{self.pacjentka} – {self.nazwa_pliku}"

    class Meta:
        ordering = ['-data_wgrania']
        verbose_name = 'Plik badań'
        verbose_name_plural = 'Pliki badań'