from django.db import models
from django.contrib.auth.models import User



class Pacjentka(models.Model):
    
    uzytkownik = models.OneToOneField(
        User,
        on_delete=models.CASCADE
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



class Pomiar(models.Model):
    TYPY_POMIAROW = [
        ('glukoza', 'Poziom glukozy (mg/dL)'),
        ('cisnienie_s', 'Ciśnienie skurczowe (mmHg)'),
        ('cisnienie_r', 'Ciśnienie rozkurczowe (mmHg)'),
        ('waga', 'Waga (kg)'),
        ('tetno', 'Tętno (uderzenia/min)'),
    ]
    SAMOPOCZUCIE_WYBORY = [
        (1, '😞 Bardzo złe'),
        (2, '😕 Złe'),
        (3, '😐 Średnie'),
        (4, '🙂 Dobre'),
        (5, '😊 Bardzo dobre'),
    ]

   
    pacjentka = models.ForeignKey(
        Pacjentka,
        on_delete=models.CASCADE,
        related_name='pomiary'
    )
    typ = models.CharField(max_length=20, choices=TYPY_POMIAROW)
    wartosc = models.FloatField()
    data_pomiaru = models.DateTimeField()
    samopoczucie = models.IntegerField(
        choices=SAMOPOCZUCIE_WYBORY,
        null=True,
        blank=True
    )
    notatka = models.TextField(blank=True)

    def __str__(self):
        return f"{self.pacjentka} – {self.typ}: {self.wartosc}"

    class Meta:
        ordering = ['-data_pomiaru']
        verbose_name = 'Pomiar'
        verbose_name_plural = 'Pomiary'



class WizytaLekarska(models.Model):
    pacjentka = models.ForeignKey(
        Pacjentka,
        on_delete=models.CASCADE,
        related_name='wizyty'
    )
    lekarz = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
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



class Recepta(models.Model):
    lekarz = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='wypisane_recepty'
    )
    
    pacjentki = models.ManyToManyField(
        Pacjentka,
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

class Lekarz(models.Model):
    uzytkownik = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )
    imie = models.CharField(max_length=100)
    nazwisko = models.CharField(max_length=100)
    miejsce_pracy = models.CharField(max_length=200)
    specjalizacja = models.CharField(max_length=100, blank=True)
    telefon = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"Dr {self.imie} {self.nazwisko}"

    class Meta:
        verbose_name = 'Lekarz'
        verbose_name_plural = 'Lekarze'

# ================================================================
# MODEL – PacjentkaLekarza
# Lekarz dodaje pacjentkę po PESEL – tworzy się relacja
# Relacja WIELE DO WIELU między Lekarzem a Pacjentką
# ================================================================
class PacjentkaLekarza(models.Model):
    lekarz = models.ForeignKey(
        User,
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
        # unique_together = lekarz może mieć pacjentkę tylko raz na liście
        unique_together = ['lekarz', 'pacjentka']
        verbose_name = 'Pacjentka lekarza'
        verbose_name_plural = 'Pacjentki lekarza'

    def __str__(self):
        return f"Dr {self.lekarz.last_name} – {self.pacjentka}"