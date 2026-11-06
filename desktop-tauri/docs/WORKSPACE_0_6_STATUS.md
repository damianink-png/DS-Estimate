# DS Estimate 0.6 — wspólny import wystąpień, podgląd i przygotowanie spoin

## Zmiany

- Import części, analizator połączeń i podgląd korzystają z jednej kolejności wystąpień XCAF. Nazwa jest pobierana razem z właściwą bryłą i jej przekształceniem w drzewie. Usunięto dopasowywanie nazw między dwoma niezależnymi importami przez zaokrąglone gabaryty i objętość.
- Brak nazwy i awaria importu drzewa są jawne. Awaria XCAF może przełączyć import na geometrię bez nazw, z komunikatem. Nie da się odtworzyć nazw, których nie zapisano w pliku.
- Podgląd rzeczywistej siatki jest przygotowywany podczas analizy i dołączany do przedmiaru, współdzielony przez zweryfikowaną grupę geometrii. Otwarcie parametrów nie wymaga kolejnego importu całego STEP. W razie braku siatki pozostaje osobny odczyt i jawny błąd; wysokość obszaru grafiki jest określona. Bardzo złożona siatka jest próbkowana równomiernie do podglądu, nie służy do pomiarów.
- Wersja 0.6.0 jest widoczna w tytule i interfejsie. Analiza odrzuca odpowiedź starszego silnika, aby nie mieszać nowego interfejsu ze starym backendem.
- Pomiar grubości wykorzystuje odległość nakładających się ścian płaskich w ich lokalnych osiach, z dopuszczeniem różnych pól skórek przy fazach i otworach. Ściany dzielone w STEP są scalane na potrzeby parowania cylindrycznych gięć.
- Stały, rozpoznany przekrój na większości próbek może dać propozycję półfabrykatu nawet przy otworze/podcięciu. Sam gotowy detal pozostaje sklasyfikowany zachowawczo, a cięcie korzysta z pola przekroju proponowanego półfabrykatu. Nie dowodzi to normy dostawy.
- Analiza przygotowania połączenia mierzy pole pustki do wypełnienia w trzech przekrojach poprzecznych. Obsługuje pryzmatyczne I, V, pół-V, X oraz fazowaną stopę połączenia T/K, także po obrocie i przy szczelinie do 3 mm. Zmierzona długość osi i pole rowka zastępują obwód styku i domyślny przekrój w obliczeniu ilości stopiwa. Czas wynika z objętości, gęstości, wydajności stapiania i wykorzystania łuku. Edycja pola/typu nadal przelicza wynik.
- Przedmiary i korekty projektu z poprzedniego schematu nie są bezpośrednio przypisywane do nowych numerów brył: nowy import może mieć inną kolejność. Stare dane pozostają w poprzedniej przestrzeni zapisu; ustawienia cen i stanowisk są zachowane. Po aktualizacji wykonaj analizę modelu ponownie.

## Granice

Pomiar rowka nie potwierdza zamiaru spawania, dostępu, wytrzymałości ani WPS. Nie obejmuje nadlewu. W pełni zamknięte, nieregularne, wielokrzywiznowe, bardzo zmienne rowki i szczeliny powyżej zakresu mogą pozostać nierozpoznane. Połączenie T bez potwierdzonej fazy pozostaje propozycją pachwinową. Kontur blachy giętej nadal jest oszacowaniem powierzchni środkowej, a nie pełnym rozwinięciem produkcyjnym. Profile po silnej obróbce lub powierzchnie aproksymowane mogą wymagać korekty. Bez STEP użytkownika nie potwierdzono modelu zgłoszonego w rozmowie.

## Weryfikacja

Regresje obejmują zagnieżdżone złożenie z sześcioma nazwanymi wystąpieniami, wspólną definicję części w różnych położeniach, obróconą płytę 15 mm, profil z wycięciem, blachę giętą 3 mm, rowki V/X ze szczeliną i fazę stopy połączenia T. Testy obliczeń sprawdzają użycie zmierzonego pola rowka oraz przekroju półfabrykatu.

Do Windows CI dodano instalację paczki NSIS i test prawdziwego WebView2, natywnego mostka i silnika CAD, bez wstrzykiwania przedmiaru ani atrap komend. Sprawdza nazwy, grafikę (także widoczne piksele i obracanie), grubości, fazę V i automatyczną zmianę czasu; zapisuje zrzuty i raport. Wynik tego testu należy odczytać z właściwego przebiegu CI — samo istnienie testu nie oznacza jego zaliczenia.
