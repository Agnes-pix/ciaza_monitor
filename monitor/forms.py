from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Pacjentka, Pomiar, WizytaLekarska, Recepta, Lekarz


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
        fields = ['imie', 'nazwisko', 'miejsce_pracy',
                  'specjalizacja', 'telefon']
        labels = {
            'imie': 'Imię',
            'nazwisko': 'Nazwisko',
            'miejsce_pracy': 'Miejsce pracy',
            'specjalizacja': 'Specjalizacja',
            'telefon': 'Telefon',
        }

class FormularzPomiaru(forms.ModelForm):
    class Meta:
        model = Pomiar
        fields = ['typ', 'wartosc', 'data_pomiaru', 'samopoczucie', 'notatka']
        widgets = {
            'data_pomiaru': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}
            ),
            'notatka': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'typ': 'Rodzaj pomiaru',
            'wartosc': 'Wartość',
            'data_pomiaru': 'Data i godzina pomiaru',
            'samopoczucie': 'Jak się czujesz?',
            'notatka': 'Notatka (opcjonalnie)',
        }


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
            'dawkowanie': 'Dawkowanie',
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