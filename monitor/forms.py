from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Pacjentka, Pomiar, WizytaLekarska, Recepta, Lekarz
from .models import Pacjentka, Pomiar, WizytaLekarska, Recepta, Lekarz, PlikBadan

# ================================================================
# FORMULARZ 1 – Rejestracja użytkownika
# Obsługuje rejestrację zarówno pacjentki jak i lekarza
# Pole 'rola' decyduje o typie konta
# ================================================================
class FormularzRejestracji(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')
    first_name = forms.CharField(max_length=100, label='Imię')
    last_name = forms.CharField(max_length=100, label='Nazwisko')

    ROLE = [
        ('pacjentka', 'Jestem pacjentką'),
        ('lekarz', 'Jestem lekarzem')
    ]
    rola = forms.ChoiceField(
        choices=ROLE,
        label='Rejestruję się jako',
        widget=forms.RadioSelect,
        initial='pacjentka'
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name',
                  'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        # Jeśli lekarz – nadaj uprawnienia staff
        if self.cleaned_data.get('rola') == 'lekarz':
            user.is_staff = True
        if commit:
            user.save()
        return user


# ================================================================
# FORMULARZ 2 – Dane medyczne pacjentki
# Uzupełnia profil pacjentki po rejestracji konta
# ================================================================
class FormularzDanePacjentki(forms.ModelForm):
    class Meta:
        model = Pacjentka
        fields = ['pesel', 'data_urodzenia',
                  'przewidywana_data_porodu', 'telefon']
        widgets = {
            'pesel': forms.TextInput(attrs={
                'placeholder': 'Wpisz 11-cyfrowy PESEL',
                'maxlength': '11',
                'minlength': '11',
            }),
            'data_urodzenia': forms.DateInput(attrs={'type': 'date'}),
            'przewidywana_data_porodu': forms.DateInput(
                attrs={'type': 'date'}
            ),
            'telefon': forms.TextInput(attrs={
                'placeholder': 'np. 500 600 700'
            }),
        }
        labels = {
            'pesel': 'Numer PESEL',
            'data_urodzenia': 'Data urodzenia',
            'przewidywana_data_porodu': 'Przewidywana data porodu',
            'telefon': 'Numer telefonu',
        }

    def clean_pesel(self):
        pesel = self.cleaned_data.get('pesel')
        if not pesel.isdigit():
            raise forms.ValidationError(
                'PESEL może zawierać tylko cyfry!'
            )
        if len(pesel) != 11:
            raise forms.ValidationError(
                'PESEL musi mieć dokładnie 11 cyfr!'
            )
        return pesel


# ================================================================
# FORMULARZ 3 – Dane zawodowe lekarza
# Uzupełnia profil lekarza po rejestracji konta
# ================================================================
class FormularzDaneLekarz(forms.ModelForm):
    class Meta:
        model = Lekarz
        fields = ['pwz', 'miejsce_pracy', 'specjalizacja', 'telefon']
        widgets = {
            'pwz': forms.TextInput(attrs={
                'placeholder': 'Wpisz 7-cyfrowy numer PWZ',
                'maxlength': '7',
                'minlength': '7',
            }),
            'miejsce_pracy': forms.TextInput(attrs={
                'placeholder': 'np. Szpital Miejski nr 5'
            }),
            'specjalizacja': forms.TextInput(attrs={
                'placeholder': 'np. Ginekolog'
            }),
            'telefon': forms.TextInput(attrs={
                'placeholder': 'np. 500 600 700'
            }),
        }
        labels = {
            'pwz': 'Numer PWZ',
            'miejsce_pracy': 'Miejsce pracy',
            'specjalizacja': 'Specjalizacja',
            'telefon': 'Telefon',
        }

    def clean_pwz(self):
        pwz = self.cleaned_data.get('pwz')
        if not pwz:
            raise forms.ValidationError('Numer PWZ jest wymagany!')
        if not pwz.isdigit():
            raise forms.ValidationError('PWZ może zawierać tylko cyfry!')
        if len(pwz) != 7:
            raise forms.ValidationError(
                'PWZ musi mieć dokładnie 7 cyfr!'
            )
        if pwz[0] == '0':
            raise forms.ValidationError(
                'PWZ nie może zaczynać się od 0!'
            )
        return pwz


# ================================================================
# FORMULARZ 4 – Dodawanie pomiaru przez pacjentkę
# Obsługuje wszystkie typy pomiarów
# Dla ciśnienia używa specjalnego pola w formacie 120/80
# ================================================================
class FormularzPomiaru(forms.ModelForm):
    # Dodatkowe pole tylko dla ciśnienia
    TYPY_CHOICES = [
        ('', '– wybierz typ –'),
        ('glukoza', 'Poziom glukozy (mg/dL)'),
        ('cisnienie', 'Ciśnienie krwi (mmHg)'),
        ('tetno', 'Tętno (uderzenia/min)'),
    ]
    
    typ = forms.ChoiceField(
        choices=TYPY_CHOICES,
        label='Rodzaj pomiaru',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_typ'
        })
    )

    cisnienie = forms.CharField(
        required=False,
        label='Ciśnienie krwi',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'np. 120/80',
            'id': 'id_cisnienie'
        })
    )

    class Meta:
        model = Pomiar
        fields = ['typ', 'wartosc', 'data_pomiaru']
        widgets = {
            # 'typ': forms.Select(attrs={
            #     'class': 'form-select',
            #     'id': 'id_typ'
            # }),
            'wartosc': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': 'np. 95.0',
                'id': 'id_wartosc'
            }),
            'data_pomiaru': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }
        labels = {
            'typ': 'Rodzaj pomiaru',
            'wartosc': 'Wartość',
            'data_pomiaru': 'Data i godzina pomiaru',
        }

    def clean(self):
        cleaned_data = super().clean()
        typ = cleaned_data.get('typ')
        cisnienie = cleaned_data.get('cisnienie')

        if typ == 'cisnienie':
            if not cisnienie:
                raise forms.ValidationError(
                    'Wpisz ciśnienie w formacie 120/80!'
                )
            if '/' not in cisnienie:
                raise forms.ValidationError(
                    'Podaj ciśnienie w formacie 120/80!'
                )
            try:
                czesci = cisnienie.split('/')
                int(czesci[0].strip())
                int(czesci[1].strip())
            except (ValueError, IndexError):
                raise forms.ValidationError(
                    'Nieprawidłowy format! Użyj np. 120/80'
                )
        return cleaned_data


# ================================================================
# FORMULARZ 5 – Samopoczucie pacjentki z notatką
# Zapisywane jako osobny typ pomiaru w bazie
# Data wypełniana automatycznie przez JavaScript
# ================================================================
class FormularzSamopoczucia(forms.ModelForm):
    class Meta:
        model = Pomiar
        fields = ['samopoczucie', 'notatka', 'data_pomiaru']
        widgets = {
            'samopoczucie': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notatka': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Jak się czujesz? Opisz swój dzień...'
            }),
            'data_pomiaru': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'id': 'id_data_samopoczucia'
            }),
        }
        labels = {
            'samopoczucie': 'Jak się czujesz?',
            'notatka': 'Notatka (opcjonalnie)',
            'data_pomiaru': 'Data i godzina',
        }


# ================================================================
# FORMULARZ 6 – Wypisanie recepty przez lekarza
# Używany w panelu lekarza – wymaga wyboru pacjentki
# ================================================================
class FormularzRecepty(forms.ModelForm):
    class Meta:
        model = Recepta
        fields = ['pacjentka', 'nazwa_leku', 'dawkowanie', 'uwagi']
        widgets = {
            'pacjentka': forms.Select(attrs={'class': 'form-select'}),
            'uwagi': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'pacjentka': 'Wybierz pacjentkę',
            'nazwa_leku': 'Nazwa leku',
            'dawkowanie': 'Ilość opakowań',
            'uwagi': 'Uwagi dla pacjentki',
        }


# ================================================================
# FORMULARZ 7 – Recepta dla konkretnej pacjentki
# Używany w szczegółach pacjentki – pacjentka przypisywana
# automatycznie z URL, bez ręcznego wyboru
# ================================================================
class FormularzReceptyDlaPacjentki(forms.ModelForm):
    class Meta:
        model = Recepta
        fields = ['nazwa_leku', 'dawkowanie', 'uwagi']
        widgets = {
            'uwagi': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'nazwa_leku': 'Nazwa leku',
            'dawkowanie': 'Ilość opakowań',
            'uwagi': 'Uwagi dla pacjentki',
        }


# ================================================================
# FORMULARZ 8 – Umawianie wizyty przez lekarza
# Używany w szczegółach pacjentki – pacjentka przypisywana
# automatycznie z URL, bez ręcznego wyboru
# ================================================================
class FormularzWizytyDlaPacjentki(forms.ModelForm):
    class Meta:
        model = WizytaLekarska
        fields = ['data_wizyty', 'miejsce', 'specjalizacja', 'notatki']
        widgets = {
            'data_wizyty': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'miejsce': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'np. Przychodnia nr 5'
            }),
            'specjalizacja': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'np. Ginekolog'
            }),
            'notatki': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
        labels = {
            'data_wizyty': 'Data i godzina wizyty',
            'miejsce': 'Miejsce (nazwa przychodni)',
            'specjalizacja': 'Rodzaj wizyty',
            'notatki': 'Notatki',
        }


# ================================================================
# FORMULARZ 9 – Wyszukiwanie pacjentki po PESEL
# Używany przez lekarza do dodania pacjentki do swojej listy
# ================================================================
class FormularzDodajPacjentkePesel(forms.Form):
    pesel = forms.CharField(
        max_length=11,
        min_length=11,
        label='Numer PESEL pacjentki',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Wpisz 11-cyfrowy PESEL',
            'maxlength': '11',
        })
    )

    def clean_pesel(self):
        pesel = self.cleaned_data.get('pesel')
        if not pesel.isdigit():
            raise forms.ValidationError('PESEL może zawierać tylko cyfry!')
        if len(pesel) != 11:
            raise forms.ValidationError('PESEL musi mieć dokładnie 11 cyfr!')
        return pesel


# ================================================================
# FORMULARZ 11 – Filtrowanie pomiarów
# Używany na stronie /pomiary/ oraz w szczegółach pacjentki
# Pola: typ pomiaru (select) oraz zakres dat (date)
# Dane przechowywane w GET (pasku adresu)
# ================================================================
class FormularzFiltrowaniaPomiarow(forms.Form):
    TYPY_FILTR = [
        ('', 'Wszystkie typy'),
        ('glukoza', 'Poziom glukozy'),
        ('cisnienie', 'Ciśnienie krwi'),
        ('tetno', 'Tętno'),
        ('samopoczucie', 'Samopoczucie'),
    ]

    typ = forms.ChoiceField(
        choices=TYPY_FILTR,
        required=False,
        label='Rodzaj pomiaru',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    data_od = forms.DateField(
        required=False,
        label='Data od',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    data_do = forms.DateField(
        required=False,
        label='Data do',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


# ================================================================
# FORMULARZ 12 – Filtrowanie pacjentek (panel lekarza)
# Pola: fragment nazwiska/imienia (text) oraz termin porodu (date)
# Dane przechowywane w GET (pasku adresu)
# ================================================================
class FormularzFiltrowaniaPacjentek(forms.Form):
    szukaj = forms.CharField(
        required=False,
        label='Imię, nazwisko lub PESEL',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'np. Kowalska lub 12345...',
        })
    )
    porod_od = forms.DateField(
        required=False,
        label='Termin porodu od',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    porod_do = forms.DateField(
        required=False,
        label='Termin porodu do',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )



# ================================================================
# FORMULARZ 10 – Wgrywanie pliku PDF z wynikami badań
# Dostępny dla pacjentki – plik przypisywany automatycznie
# Walidacja: tylko PDF, maksymalnie 10MB
# ================================================================
class FormularzPlikuBadan(forms.ModelForm):
    class Meta:
        model = PlikBadan
        fields = ['plik', 'opis']
        widgets = {
            'plik': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf'  # przeglądarka pokazuje tylko PDF
            }),
            'opis': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'np. Wyniki morfologii 10.03.2026'
            }),
        }
        labels = {
            'plik': 'Wybierz plik PDF',
            'opis': 'Opis pliku (opcjonalnie)',
        }

    def clean_plik(self):
        plik = self.cleaned_data.get('plik')
        if plik:
            if not plik.name.lower().endswith('.pdf'):
                raise forms.ValidationError(
                    'Dozwolone są tylko pliki PDF!'
                )
            # Maksymalny rozmiar: 10MB
            if plik.size > 10 * 1024 * 1024:
                raise forms.ValidationError(
                    'Plik jest za duży! Maksymalny rozmiar to 10MB.'
                )
        return plik