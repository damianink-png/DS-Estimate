# DS Estimate 0.4 — detale i automatyzacja

## Wdrożone

- Osobne ustawienia każdego wystąpienia: nazwa/ID, geometria, wymiary, materiał,
  własna gęstość, masa gotowa, sześć naddatków i masa półfabrykatu.
- Pusty gatunek i 7850 kg/m³ bez materiału. Zmiana jednego detalu nie zmienia
  innych wystąpień z tej samej grupy. Starsze ustawienia grup są migrowane.
- Produkcja własna / zakup / kooperacja na każdym detalu. Cena dostawcy za detal;
  wybór, czy kooperacja obejmuje materiał. Własne cięcie pomija elementy zewnętrzne.
- Biblioteka 1792 przekrojów offline: IPE, IPN, HEA/B/M, UPN/UPE, RHS/SHS/CHS,
  kątowniki i płaskowniki. Dopasowanie nominalne, także z wyborem niejednoznacznych
  wariantów; nie dowodzi konkretnej normy dostawy ani materiału.
- Usprawnione rozpoznawanie obróconych brył i zaokrąglonych naroży profili.
- Cięcie: płyta do 10 mm — preferowany laser; grubsza — plazma/palnik w zakresie
  materiału/maszyny; profile — piła. Posuw wg edytowalnej tabeli grubości, pole
  piły, liczba cięć i kąt, przebicia, obsługa, przezbrojenie raz na partię.
- Lista cięcia posortowana według maszyny, materiału, grubości / przekroju.
- Spawanie: osobna analiza dokładnych styków B-Rep. Kandydaci ścian/krawędzi,
  odrzucenie kolizji, korekty długości, a lub pola rowka, gęstości i włączenia.
  Zestawienie długości wg przekroju i czasu spawania. Początkowe a jest heurystyką
  kosztową z grubości i limitu operatora, nie doborem nośności spoiny.
- Gięcie: pary cylindrycznych ścian jako kandydaci gięć, ręczna liczba na detalu,
  cykl i przezbrojenie. Naroża gotowych profili nie naliczają gięcia prasy.
- CNC: szacunek objętości do usunięcia z naddatków i dotychczasowe kalkulatory.
- Montaż, VT, szlifowanie, powłoki, pakowanie, przewóz i technologia: jawne normy
  zakładowe, część domyślnie wyłączona; wyniki w kolumnie automatycznej, obok korekty.
- Eksport JSON i CSV obejmuje stan modułów i dane detali; JSON także kandydatów spoin.

## Granice działania

1. Nie każdy kształt jest wyrobem katalogowym. Fazy, otwory, cięcia ukośne i zmienny
   przekrój mogą wymagać wyboru wyrobu ręcznie. Podobna geometria nie identyfikuje
   jednoznacznie procesu walcowania, normy ani gatunku.
2. Obwód kontaktu jest propozycją spawania dookoła. Śruby, oparcia, styki podzielonych
   ścian i brak dostępu wymagają wyłączenia/korekkt. Fazy i rzeczywisty rowek nie są
   rozpoznawane automatycznie; dla spoiny czołowej podaje się pole przekroju.
3. Analiza styków ma limit par/czasu i raportuje niepełny wynik. Szczeliny bez styku
   i niewymodelowane elementy nie są rekonstruowane automatycznie.
4. Brak pełnego rozwinięcia blach, nestingu arkuszy/sztang i CAM. Brak konturu nie jest
   zastępowany obwodem gabarytów. Nie ma jeszcze podglądu 3D detalu.
5. Masa półfabrykatu z naddatków jest szacunkiem proporcji gabarytów. Można wpisać
   znaną masę. Powierzchnia powłok jest sumą brutto B-Rep, z powierzchniami styku.
6. Kształtowe grupowanie nadal pochodzi z OCCT; pełna hierarchia/nazwy XCAF BOM nie
   są gwarantowane. Nazwy brył STEP są odczytywane, gdy translator je udostępnia.
7. NDT, wymagania jakości, rzeczywiste narzędzia i dostęp wymagają technologii operatora.

Źródła, licencje i decyzje o wykorzystaniu:
[OPEN_SOURCE_MODULE_AUDIT.md](OPEN_SOURCE_MODULE_AUDIT.md).

## Sprawdzenia

Testy Node: niezależne materiały dwóch identycznych wystąpień, sześć naddatków,
zakup/kooperacja bez dublowania kosztów, granica 10 mm, partie/przezbrojenia,
piła i kąt, brak fałszywego konturu, korekty spoin, normy oraz eksport.

Testy rzeczywistej geometrii OCCT: obrócony profil i blacha, zaokrąglony SHS,
nominalne dopasowanie IPE, styk ścian, styk krawędzi, punkt, szczelina, kolizja,
limit detekcji i cylindryczna para gięcia. Lokalny test używa OCP; Windows CI
sprawdza pythonocc-core i skompilowany EXE z opcją --joints. Test przeglądarkowy
symuluje mostek natywny i nie zastępuje testów skompilowanego backendu.
