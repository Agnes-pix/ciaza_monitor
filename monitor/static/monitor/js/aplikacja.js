// ============================================================
// PLIK: aplikacja.js
// Zawiera 3 elementy dynamiczne wymagane w części 4:
// 1. Animowane pojawianie się kart
// 2. Walidacja formularza w czasie rzeczywistym
// 3. Wykres pomiarów (Chart.js)
// ============================================================


// document.addEventListener('DOMContentLoaded', funkcja) =
// Uruchom cały kod dopiero gdy strona HTML jest w pełni załadowana
// Bez tego JavaScript mógłby szukać elementów które jeszcze nie istnieją
document.addEventListener('DOMContentLoaded', function () {


    // ========================================================
    // ELEMENT 1 – Animowane pojawianie się kart
    // ========================================================
    // Co to robi: każda karta (.card) pojawia się z małym
    // opóźnieniem – jedna po drugiej, "wjeżdżając" z dołu
    // ========================================================

    // querySelectorAll = znajdź WSZYSTKIE elementy z klasą .card
    // Zwraca listę (jak tablicę) wszystkich kart na stronie
    const karty = document.querySelectorAll('.card');

    // forEach = dla każdej karty wykonaj funkcję
    // index = numer kolejny karty (0, 1, 2, 3...)
    karty.forEach(function(karta, index) {

        // Na starcie każda karta jest:
        // - niewidoczna (opacity: 0)
        // - przesunięta 30px w dół (translateY: 30px)
        karta.style.opacity = '0';
        karta.style.transform = 'translateY(30px)';

        // transition = animacja CSS
        // "opacity 0.5s ease" = zmiana przezroczystości przez 0.5 sekundy
        // "transform 0.5s ease" = animacja przesunięcia przez 0.5 sekundy
        karta.style.transition = 'opacity 0.5s ease, transform 0.5s ease';

        // setTimeout = wykonaj kod po określonym czasie (w ms)
        // index * 100 = każda kolejna karta czeka 100ms dłużej
        // Karta 0 = pojawia się po 0ms
        // Karta 1 = pojawia się po 100ms
        // Karta 2 = pojawia się po 200ms
        // Dzięki temu karty pojawiają się jedna po drugiej!
        setTimeout(function() {
            karta.style.opacity = '1';           // staje się widoczna
            karta.style.transform = 'translateY(0)'; // wraca na miejsce
        }, index * 100);
    });


    // ========================================================
    // ELEMENT 2 – Walidacja formularza w czasie rzeczywistym
    // ========================================================
    // Co to robi: gdy pacjentka wpisuje wartość pomiaru,
    // natychmiast sprawdzamy czy jest w normie i pokazujemy
    // odpowiedni komunikat – BEZ wysyłania formularza!
    // ========================================================

    // querySelector = znajdź PIERWSZY element pasujący do selektora
    // Szukamy pola input o nazwie "wartosc"
    const poleWartosc = document.querySelector('input[name="wartosc"]');

    if (poleWartosc) {
        // Tworzymy nowy element <div> który będzie wyświetlał komunikat
        const komunikat = document.createElement('div');
        // Ustawiamy klasy Bootstrap żeby ładnie wyglądał
        komunikat.className = 'small mt-1';
        // insertAdjacentElement = wstaw element zaraz PO polu input
        poleWartosc.insertAdjacentElement('afterend', komunikat);

        // Zakresy norm dla każdego rodzaju pomiaru
        // Gdy pacjentka wybierze typ, sprawdzamy czy wartość jest w normie
        const normy = {
            'glukoza':     { min: 70,  max: 140, jednostka: 'mg/dL' },
            'cisnienie_s': { min: 90,  max: 140, jednostka: 'mmHg'  },
            'cisnienie_r': { min: 60,  max: 90,  jednostka: 'mmHg'  },
            'waga':        { min: 40,  max: 120, jednostka: 'kg'    },
            'tetno':       { min: 60,  max: 100, jednostka: '/min'  },
        };

        // 'input' = zdarzenie które odpala się za każdym razem
        // gdy użytkownik cokolwiek wpisze w pole
        poleWartosc.addEventListener('input', function() {

            // parseFloat = zamień tekst na liczbę
            // np. "95.5" → 95.5
            const wartosc = parseFloat(this.value);

            // Pobieramy aktualnie wybrany typ pomiaru
            const selectTyp = document.querySelector('select[name="typ"]');
            const typ = selectTyp ? selectTyp.value : '';

            if (isNaN(wartosc) || this.value === '') {
                // Pole puste lub wpisano tekst zamiast liczby
                komunikat.innerHTML = '';
                poleWartosc.classList.remove('is-valid', 'is-invalid');

            } else if (wartosc <= 0) {
                // Wartość ujemna lub zero
                komunikat.innerHTML =
                    '<span class="text-danger">' +
                    '<i class="bi bi-x-circle me-1"></i>' +
                    'Wartość musi być większa od zera' +
                    '</span>';
                poleWartosc.classList.add('is-invalid');
                poleWartosc.classList.remove('is-valid');

            } else if (typ && normy[typ]) {
                // Znamy typ – sprawdzamy czy w normie
                const norma = normy[typ];

                if (wartosc < norma.min || wartosc > norma.max) {
                    // POZA normą – ostrzeżenie
                    komunikat.innerHTML =
                        '<span class="text-warning">' +
                        '<i class="bi bi-exclamation-triangle me-1"></i>' +
                        'Wartość poza normą! Norma: ' +
                        norma.min + '–' + norma.max + ' ' + norma.jednostka +
                        '. Skonsultuj z lekarzem.' +
                        '</span>';
                    poleWartosc.classList.remove('is-valid', 'is-invalid');

                } else {
                    // W normie – zielony komunikat
                    komunikat.innerHTML =
                        '<span class="text-success">' +
                        '<i class="bi bi-check-circle me-1"></i>' +
                        'Wartość w normie ✓' +
                        '</span>';
                    poleWartosc.classList.add('is-valid');
                    poleWartosc.classList.remove('is-invalid');
                }
            } else {
                // Nie znamy typu – pokazujemy że liczba jest OK
                komunikat.innerHTML =
                    '<span class="text-success">' +
                    '<i class="bi bi-check-circle me-1"></i>' +
                    'Poprawna liczba' +
                    '</span>';
                poleWartosc.classList.add('is-valid');
                poleWartosc.classList.remove('is-invalid');
            }
        });

        // Gdy zmienia się typ pomiaru – przelicz walidację od nowa
        const selectTyp = document.querySelector('select[name="typ"]');
        if (selectTyp) {
            // 'change' = zdarzenie gdy użytkownik wybierze inną opcję
            selectTyp.addEventListener('change', function() {
                // dispatchEvent = "udawaj" że użytkownik coś wpisał
                // żeby uruchomić ponownie walidację wartości
                poleWartosc.dispatchEvent(new Event('input'));
            });
        }
    }


    // ========================================================
    // ELEMENT 3 – Dynamiczne tworzenie podglądu pomiaru
    // ========================================================
    // Co to robi: gdy pacjentka wypełnia formularz pomiaru,
    // na bieżąco tworzy się karta podglądu pokazująca
    // jak będzie wyglądał zapisany pomiar
    // ========================================================

    // Szukamy formularza pomiaru po ukrytym polu akcja
    const formularzPomiaru = document.querySelector(
        'input[name="akcja"][value="dodaj_pomiar"]'
    );

    if (formularzPomiaru) {

        // Tworzymy kontener na podgląd
        const kontener = document.createElement('div');
        kontener.id = 'podglad-pomiaru';
        kontener.className = 'mt-3';
        // Wstawiamy go za formularzem
        formularzPomiaru.closest('form').insertAdjacentElement(
            'afterend', kontener
        );

        // Funkcja która buduje kartę podglądu
        function aktualizujPodglad() {
            const typ = document.querySelector('select[name="typ"]');
            const wartosc = document.querySelector('input[name="wartosc"]');
            const data = document.querySelector('input[name="data_pomiaru"]');
            const samopoczucie = document.querySelector(
                'select[name="samopoczucie"]'
            );

            // Pobieramy teksty z wybranych opcji
            const typTekst = typ && typ.selectedIndex > 0
                ? typ.options[typ.selectedIndex].text : null;
            const wartoscTekst = wartosc && wartosc.value
                ? wartosc.value : null;

            // Jeśli nic nie wypełniono – ukryj podgląd
            if (!typTekst && !wartoscTekst) {
                kontener.innerHTML = '';
                return;
            }

            // Formatuj datę na czytelną formę
            let dataTekst = '—';
            if (data && data.value) {
                const d = new Date(data.value);
                dataTekst = d.toLocaleString('pl-PL');
            }

            const samopoczucieTekst = samopoczucie &&
                samopoczucie.selectedIndex > 0
                ? samopoczucie.options[samopoczucie.selectedIndex].text
                : '—';

            // innerHTML = tworzymy kartę HTML dynamicznie przez JavaScript!
            // To jest właśnie "dynamiczne tworzenie elementów"
            kontener.innerHTML =
                '<div class="card border-primary" ' +
                'style="opacity:0; transform:translateY(10px);' +
                'transition: opacity 0.3s, transform 0.3s;">' +
                '<div class="card-header bg-primary text-white">' +
                '<i class="bi bi-eye me-2"></i>Podgląd pomiaru' +
                '</div>' +
                '<div class="card-body">' +
                '<div class="row">' +
                '<div class="col-6">' +
                '<small class="text-muted">Rodzaj</small><br>' +
                '<strong>' + (typTekst || '—') + '</strong>' +
                '</div>' +
                '<div class="col-6">' +
                '<small class="text-muted">Wartość</small><br>' +
                '<strong class="text-primary fs-5">' +
                (wartoscTekst || '—') + '</strong>' +
                '</div>' +
                '<div class="col-6 mt-2">' +
                '<small class="text-muted">Data</small><br>' +
                '<strong>' + dataTekst + '</strong>' +
                '</div>' +
                '<div class="col-6 mt-2">' +
                '<small class="text-muted">Samopoczucie</small><br>' +
                '<strong>' + samopoczucieTekst + '</strong>' +
                '</div>' +
                '</div>' +
                '</div>' +
                '<div class="card-footer text-muted small">' +
                '<i class="bi bi-info-circle me-1"></i>' +
                'Podgląd – kliknij "Zapisz pomiar" aby zapisać' +
                '</div>' +
                '</div>';

            // Animujemy pojawienie się podglądu
            // requestAnimationFrame = poczekaj na następną klatkę animacji
            requestAnimationFrame(function() {
                const nowaKarta = kontener.querySelector('.card');
                if (nowaKarta) {
                    nowaKarta.style.opacity = '1';
                    nowaKarta.style.transform = 'translateY(0)';
                }
            });
        }

        // Nasłuchujemy zmian na wszystkich polach formularza
        ['select[name="typ"]', 'input[name="wartosc"]',
         'input[name="data_pomiaru"]', 'select[name="samopoczucie"]'
        ].forEach(function(selektor) {
            const pole = document.querySelector(selektor);
            if (pole) {
                // Dla selectów używamy 'change', dla inputów 'input'
                const zdarzenie = pole.tagName === 'SELECT' ? 'change' : 'input';
                pole.addEventListener(zdarzenie, aktualizujPodglad);
            }
        });
    }

}); // koniec DOMContentLoaded