# DS Estimate 0.7.1 — produkty STEP, zakres operacji i analiza kontaktów

## Zmiany względem 0.7.0

- Import zapisuje oddzielną tożsamość wystąpienia produktu, definicji produktu oraz indeks i liczbę brył. To klucze drzewa XCAF; jednakowa nazwa lub objętość nie scala produktów. Import awaryjny bez wiarygodnej tożsamości nie grupuje brył jako jednego produktu.
- Zakup i kooperacja są rozliczane raz za wystąpienie produktu STEP. W prasie pięć brył podnośnika staje się jednym produktem, podobnie pięć brył szafki. Cena i sposób realizacji są edytowane razem dla brył tego produktu; materiał i naddatki nadal osobno dla bryły. Sprzeczne ceny / realizacje w starych danych nie są arbitralnie wybierane. Jednostkę handlową należy potwierdzić z dostawcą: produkt STEP nie jest gwarantowaną pozycją BOM.
- Eksport JSON i CSV oddziela produktową ofertę od brył geometrycznych. Cena produktu nie jest sumowana ponownie dla każdej bryły.
- Kontrola wymiarów rozdziela pierwsze sztuki geometrii i materiału, powtórzenia oraz próbki dostaw. Domyślne normy: przygotowanie 10 min, pierwsza sztuka 1 min, powtórzenie 0,25 min, udział próbek dostaw 10% zaokrąglany w górę osobno dla definicji produktu, próbka 0,25 min. Wszystko pozostaje edytowalną normą.
- Nieustalony zakres dodatkowego wiercenia, NDT oraz obróbki po spawaniu nie otrzymuje automatycznego zera. W ustawieniach można jawnie przyjąć brak danej operacji, dla NDT również normę czasu. Nadal można wpisać korektę czasu w module. Dla nierozpoznanych półfabrykatów zakres obróbki pozostaje nieustalony.
- Powłoki domyślnie dotyczą części produkowanych; ustawienie pozwala objąć także zakupowe. Pakowanie liczy produkty STEP, nie bryły. Opłata za kilometr nie oznacza ustalonego czasu przejazdu — ten pozostaje osobną brakującą wartością.
- Suma materiału w interfejsie jest opisana jako policzony zakres, ze wskazaniem pozycji bez kosztu. Nie jest przedstawiana jako pełny zerowy koszt przy pustych cenach.
- Analiza kontaktów współdzieli pomiar skórek dla danego wystąpienia i wcześniej odrzuca przenikające bryły. Rejestruje wszystkie pary kwalifikujące się do sprawdzenia, pary zakończone i pozostałe. Częściowo policzona para po upływie budżetu jest odrzucana zamiast dodawania skróconej spoiny.
- `complete` opisuje zakończenie sprawdzania; oddzielne `geometryValid` blokuje pełne czasy zależnych operacji przy przenikaniach lub błędach. Użytkownik widzi objętość przenikania, limit oraz pokrycie analizy. Limit 1–600 s i ponowienie analizy są dostępne w ustawieniach. Jest to budżet pomiędzy wywołaniami jądra CAD, nie twarde przerwanie pojedynczej operacji natywnej.
- Aktualizacja zachowuje korekty użytkownika, ale nie przenosi starych potwierdzeń wyceny na nową metodę obliczeń. Stare wyniki styków wymagają ponownego przeliczenia.

## Test prasy autorstwa Woods / Brooks / Pearce

Źródło: https://doi.org/10.1016/j.ohx.2024.e00566, STEP https://osf.io/nbxzq/download, SHA-256 `334286309490685981929f69e71b4bdf99d23bc5f7ccd65fd4db48e1f823cb51`.

- 220 brył i 212 wystąpień produktów STEP; wśród nich 167 brył zakupowych tworzy 159 produktów STEP. Nie jest to potwierdzona lista zamówień handlowych.
- Masa geometryczna nie zmienia się: 51,76776944 kg przy umownej gęstości 7850 kg/m³. Wcześniejsza niezależna pełna siatka: 51,76513722 kg, różnica 0,005085%.
- Kontrola według nowych norm: 19 pierwszych sztuk, 34 powtórzenia, 22 próbki dostaw. `10 + 19 × 1 + 34 × 0,25 + 22 × 0,25 = 43 min`, zamiast wcześniejszych 230 min naliczanych na wszystkie bryły. To porównanie norm, nie pomiar rzeczywistej kontroli.
- Lokalny przebieg kontaktów przy limicie 300 s zakończył wszystkie 161 kwalifikujących się par w ok. 42 s. Pozostało 10 zgłoszeń przenikań. Pełna enumeracja nie oznacza poprawnej technologii spawania; `geometryValid=false` pozostawia całkowite czasy montażu i spawania nieustalone.
- 14 nierozpoznanych zakresów obróbki nie jest już pokazywanych jako zerowe frezowanie. Wiercenie, NDT i obróbka końcowa wymagają ustalenia zakresu z dokumentacji lub jawnej decyzji w ustawieniach.

## Weryfikacja i ograniczenia

Testy obejmują jedną cenę produktu wielobryłowego, osobne wystąpienia o jednakowych nazwach, konflikty cen, próbkowanie kontroli, nieustalone wymagania rysunku, NDT normowe, brak zerowego czasu jazdy, odrzucanie przerwanej pary i blokadę wyceny przy kolizjach. Test dużego STEP w Windows sprawdza również 212 produktów i pięć brył podnośnika jako jedno wystąpienie produktu. Osobny test uruchamia zainstalowaną aplikację; wynik należy sprawdzić w końcowym przebiegu CI.

Nie naprawiono źródłowego CAD i nie zastąpiono rysunku wykonawczego domysłami. Nie ma gwarancji jednostek BOM, dostępu do spoin, WPS, pełnego rozwinięcia ani poprawności norm danego zakładu. Zwiększenie limitu nie usuwa kolizji i nie potwierdza zamiaru spawania.
