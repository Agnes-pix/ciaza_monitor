from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from .models import Pacjentka, Pomiar, WizytaLekarska, Recepta, Lekarz, PacjentkaLekarza

class FormularzRejestracji(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')
    first_name = forms.CharField(max_length=100, label='Imię')
    last_name = forms.CharField(max_length=100, label='Nazwisko')

    ROLE =[
        ('pacjentka', 'Jestem pacjentką'), 
        ('lekarz', 'Jestem lekarzem')
    ]

    rola = forms.ChoiceField(
        choices= ROLE,
        label='Rejestruje sie jako: ',
        widget= forms.RadioSelect
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name',
                  'email', 'password1', 'password2', 'rola']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        if self.cleaned_data['rola']== 'lekarz':
            user.is_staff = True
        if commit:
            user.save()
        return user


class FormularzDanePacjentki(forms.ModelForm):
    class Meta:
        model = Pacjentka
        fields = ['data_urodzenia', 'przewidywana_data_porodu', 'telefon']
        widgets = {
            'data_urodzenia': forms.DateInput(attrs={'type': 'date'}),
            'przewidywana_data_porodu': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'data_urodzenia': 'Data urodzenia',
            'przewidywana_data_porodu': 'Przewidywana data porodu',
            'telefon': 'Numer telefonu',
        }


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

    # Walidacja PWZ
    def clean_pwz(self):
        pwz = self.cleaned_data.get('pwz')
        if not pwz:
            raise forms.ValidationError('Numer PWZ jest wymagany!')
        # isdigit() = sprawdź czy wszystkie znaki to cyfry
        if not pwz.isdigit():
            raise forms.ValidationError('PWZ może zawierać tylko cyfry!')
        if len(pwz) != 7:
            raise forms.ValidationError('PWZ musi mieć dokładnie 7 cyfr!')
        # PWZ nie może zaczynać się od 0
        if pwz[0] == '0':
            raise forms.ValidationError('PWZ nie może zaczynać się od 0!')
        return pwz
    

class FormularzPomiaru(forms.ModelForm):
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
        fields = ['typ', 'wartosc', 'data_pomiaru' ]
        widgets = {
            'typ': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_typ'
            }),
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
        # clean() = walidacja całego formularza (nie jednego pola)
        cleaned_data = super().clean()
        typ = cleaned_data.get('typ')
        cisnienie = cleaned_data.get('cisnienie')

        if typ == 'cisnienie':
            # Gdy wybrano ciśnienie – pole cisnienie jest wymagane
            if not cisnienie:
                raise forms.ValidationError(
                    'Wpisz ciśnienie w formacie 120/80!'
                )
            # Sprawdzamy czy format jest poprawny
            if '/' not in cisnienie:
                raise forms.ValidationError(
                    'Podaj ciśnienie w formacie 120/80 (skurczowe/rozkurczowe)!'
                )
            try:
                czesci = cisnienie.split('/')
                int(czesci[0].strip())  # skurczowe
                int(czesci[1].strip())  # rozkurczowe
            except (ValueError, IndexError):
                raise forms.ValidationError(
                    'Nieprawidłowy format! Użyj np. 120/80'
                )
        return cleaned_data


class FormularzWizyty(forms.ModelForm):
    class Meta:
        model = WizytaLekarska
        fields = ['data_wizyty', 'miejsce', 'specjalizacja', 'notatki']
        widgets = {
            'data_wizyty': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}
            ),
            'notatki': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'data_wizyty': 'Data i godzina wizyty',
            'miejsce': 'Miejsce (nazwa przychodni)',
            'specjalizacja': 'Rodzaj wizyty (np. Ginekolog)',
            'notatki': 'Dodatkowe notatki',
        }


class FormularzRecepty(forms.ModelForm):
    class Meta:
        model = Recepta
        fields = ['pacjentki', 'nazwa_leku', 'dawkowanie', 'uwagi']
        widgets = {
            'pacjentki': forms.CheckboxSelectMultiple(),
            'uwagi': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'pacjentki': 'Wybierz pacjentkę',
            'nazwa_leku': 'Nazwa leku',
            'dawkowanie': 'Ilość opakowań',
            'uwagi': 'Uwagi dla pacjentki',
        }


class FormularzWizytyLekarza(forms.ModelForm):
    class Meta:
        model = WizytaLekarska
        fields = ['pacjentka', 'data_wizyty', 'miejsce',
                  'specjalizacja', 'notatki']
        widgets = {
            'data_wizyty': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}
            ),
            'notatki': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'pacjentka': 'Pacjentka',
            'data_wizyty': 'Data i godzina wizyty',
            'miejsce': 'Miejsce',
            'specjalizacja': 'Rodzaj wizyty',
            'notatki': 'Notatki',
        }

class FormularzDanePacjentki(forms.ModelForm):
    class Meta:
        model = Pacjentka
        fields = ['pesel', 'data_urodzenia', 'przewidywana_data_porodu', 'telefon']
        widgets = {
            'pesel': forms.TextInput(attrs={
                'placeholder': 'Wpisz 11-cyfrowy PESEL',
                'maxlength': '11',
                'minlength': '11',
            }),
            'data_urodzenia': forms.DateInput(attrs={'type': 'date'}),
            'przewidywana_data_porodu': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'pesel': 'Numer PESEL',
            'data_urodzenia': 'Data urodzenia',
            'przewidywana_data_porodu': 'Przewidywana data porodu',
            'telefon': 'Numer telefonu',
        }

    # Walidacja PESEL – sprawdzamy czy ma 11 cyfr
    def clean_pesel(self):
        pesel = self.cleaned_data.get('pesel')
        # isdigit() = sprawdź czy wszystkie znaki to cyfry
        if not pesel.isdigit():
            raise forms.ValidationError('PESEL może zawierać tylko cyfry!')
        if len(pesel) != 11:
            raise forms.ValidationError('PESEL musi mieć dokładnie 11 cyfr!')
        return pesel


# ================================================================
# FORMULARZ – Dodawanie pacjentki przez lekarza po PESEL
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
# FORMULARZ – Samopoczucie z notatką
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
            # Ukryte pole – wypełniane automatycznie przez JavaScript
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

class FormularzReceptyDlaPacjentki(forms.ModelForm):
    """Formularz recepty bez wyboru pacjentki – używany w szczegółach"""
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

class FormularzWizytyDlaPacjentki(forms.ModelForm):
    """Formularz wizyty bez wyboru pacjentki – używany w szczegółach"""
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