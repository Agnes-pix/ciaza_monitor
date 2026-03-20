from django.contrib import admin
from .models import Pacjentka, Pomiar, WizytaLekarska, Recepta, Lekarz


admin.site.register(Lekarz)
admin.site.register(Pacjentka)
admin.site.register(Pomiar)
admin.site.register(WizytaLekarska)
admin.site.register(Recepta)