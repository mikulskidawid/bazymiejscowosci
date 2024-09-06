# --- Generator bazy z miejscowościami ---
# --- Program stworzył: Dawid Mikulski ---

# --- Import bibliotek: ---

import overpy
import csv
import time

# --- Funkcje: ---

# Funkcja do pobierania jednostek administracyjnych
def pobierz_jednostki(admin_level, area_name="Polska"):

    query = f"""
    [out:json];
    area["name"="{area_name}"]->.country;
    relation["admin_level"="{admin_level}"](area.country);
    out body center;
    """

    result = api.query(query)
    return result.relations

# Funkcja do pobierania listy miejscowości dla danego powiatu
def pobierz_miejsca(area_id):

    area_id = 3600000000 + area_id # poprawka ID
    query = f"""
    [out:json];
    area({area_id})->.boundary;
    (
      node["place"~"village|hamlet|town|city"](area.boundary);
      way["place"~"village|hamlet|town|city"](area.boundary);
      relation["place"~"village|hamlet|town|city"](area.boundary);
    );
    out center tags;
    """
    
    try:
        print(f"  Pobieranie miejscowości w obszarze o ID: {area_id}")
        result = api.query(query)
        return result.nodes + result.ways + result.relations
    except overpy.exception.OverpassTooManyRequests as e:
        print(f"Zbyt wiele żądań do API Overpass, spróbuj ponownie później. Błąd: {e}")
        return []
    except Exception as e:
        print(f"Wystąpił błąd podczas pobierania miejscowości: {e}")
        return []

# Funkcja do przetworzenia relacji na listę danych (nazwa, ID, współrzędne centralne)
def pobierz_relacje(rel):
    name = rel.tags.get("name", "N/A")
    lat = rel.center_lat if hasattr(rel, 'center_lat') else "N/A"
    lon = rel.center_lon if hasattr(rel, 'center_lon') else "N/A"
    return name, lat, lon

# --- Reszta skryptu: ---

print("Generator bazy polskich miast i miejscowosci")
print("____________________________________________")

# Nazwa pliku do zapisu
csv_filename = str(input("Podaj nazwę pliku do zapisu: "))

# Zapis czasu rozpoczęcia
start_time = time.time()

# Połączenie z API Overpass
print("Łączenie z Overpass API...")
api = overpy.Overpass()

# Pobieranie listy województw
print("[1/3] Pobieranie województw...")
wojewodztwa = pobierz_jednostki(4)
liczba_wojewodztw = 16
nr_wojewodztwa = 1

# Lista wyników do zapisu do CSV
wyniki = []

print("[2/3] Przetwarzanie województw...")

# Pobieranie powiatów oraz miejscowości
for woj in wojewodztwa:
    wojewodztwo_name, woj_lat, woj_lon = pobierz_relacje(woj)
    if "województwo" in wojewodztwo_name.lower() and "admin_level" in woj.tags and "boundary" in woj.tags:
        print(f"Przetwarzanie województwa: {wojewodztwo_name} | {nr_wojewodztwa}/{liczba_wojewodztw}")
        
        # Pobieranie powiatów w danym województwie
        print(f"Pobieranie powiatów dla województwa: {wojewodztwo_name} | {nr_wojewodztwa}/{liczba_wojewodztw}")
        powiaty = pobierz_jednostki(6, wojewodztwo_name)

        powiaty_len = len(powiaty)
        print(f"Pobrano {powiaty_len} wyników. Sprawdzanie i dodawanie powiatów...")
        print("___________________________________________________________________")
        
        for powiat in powiaty:
            #print(powiat.tags)
            powiat_name, powiat_lat, powiat_lon = pobierz_relacje(powiat)
            
            # Sprawdzenie, czy jest to powiat
            if "powiat" in powiat_name.lower() and "admin_level" in powiat.tags and "boundary" in powiat.tags:
                print(f"  Przetwarzanie powiatu: {powiat_name}")
                
                # Pobieranie miejscowości w danym powiecie
                print(f"  Pobieranie miejscowości dla powiatu: {powiat_name}...")
                miejscowosci = pobierz_miejsca(powiat.id)
                print(f"  Pobrano {len(miejscowosci)} elementów dla powiatu: {powiat_name}")
                
                if not miejscowosci:
                    print(f"  Brak miejscowości w powiecie: {powiat_name} lub wystąpił błąd.")
                else:
                    for miejscowosc in miejscowosci:
                        # Pomijanie miejscowości bez nazwy
                        miejscowosc_name = miejscowosc.tags.get("name", "N/A")
                        if miejscowosc_name == "N/A": continue
                        
                        if isinstance(miejscowosc, overpy.Node):
                            miejscowosc_lat = miejscowosc.lat
                            miejscowosc_lon = miejscowosc.lon
                        else:
                            miejscowosc_lat = miejscowosc.center_lat
                            miejscowosc_lon = miejscowosc.center_lon
                        
                        wyniki.append([wojewodztwo_name, powiat_name, miejscowosc_name, miejscowosc_lat, miejscowosc_lon])

            # Sprawdzenie, czy jest to miasto
            elif "admin_level" in powiat.tags and "boundary" in powiat.tags and "name:prefix" in powiat.tags:
                if powiat.tags['name:prefix'] == "miasto na prawach powiatu":
                    print(f"  Przetwarzanie miasta na prawach powiatu: {powiat_name}")

                    if isinstance(powiat, overpy.Node):
                        miasto_lat = powiat.lat
                        miasto_lon = powiat.lon
                    else:
                        miasto_lat = powiat.center_lat
                        miasto_lon = powiat.center_lon

                    wyniki.append([wojewodztwo_name, "-", powiat_name, miasto_lat, miasto_lon])
                    print(f"    Dodano miasto na prawach powiatu: {powiat_name} (lat: {miasto_lat}, lon: {miasto_lon})")

    nr_wojewodztwa+=1

# Zapisanie danych do pliku CSV
csv_filename += '.csv'
print(f"[3/3] Zapisanie danych do pliku: {csv_filename}...")
with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["wojewodztwo", "powiat", "miejscowosc", "szerokosc_geo", "dlugosc_geo"])
    writer.writewyniki(wyniki)

# Zakończenie i obliczenie czasu działania skryptu
end_time = time.time()
execution_time = end_time - start_time
print(f"Zapisano dane miejscowości do {csv_filename}.")
print(f"Czas wykonania skryptu: {execution_time:.2f} sekundy.")
