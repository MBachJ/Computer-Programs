# Importer nødvendige biblioteker
from datetime import datetime, timedelta
import sqlite3
import os
import ast
import re
import ast
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

# Databasenavn
DATABASE = "ships_data.db"

def extract_ship_data(line):
    # Mønster koden skal kjenne igjen i dataen fra deteksjon
    pattern = r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\s+boat\s+(\d\.\d+)\s+(detected_ship.*?\.jpg)\/(detected_ship.*?\.jpg)\s+Box coordinates: \[UPPER LEFT\((\d+), (\d+)\), LOWER RIGHT\((\d+), (\d+)\)\]\s+Coords: \((\d+\.\d+), (\d+\.\d+)\)"
    print("Reading file...")
    match = re.match(pattern, line)
    if match:
        print("Match in detection data!")
        timestamp, confidence, image_name_1, image_name_2, upper_left_x, upper_left_y, lower_right_x, lower_right_y, latitude, longitude = match.groups()
        box_coords = [(int(upper_left_x), int(upper_left_y)), (int(lower_right_x), int(lower_right_y))]
        extracted_data = {
            "timestamp": timestamp,
            "confidence": float(confidence),
            "image_name": image_name_1,
            "box_coords": box_coords,  # Fortsatt som en liste av tuples
            "latitude": float(latitude),
            "longitude": float(longitude)
        }
        print("Data extracted") # legger til utskrift for debugging
        return extracted_data

def get_ship_details_from_AIS(timestamp, latitude, longitude):
    # Konverter timestamp fra streng til datetime-objekt
    timestamp2 = datetime.strptime(timestamp, '%Y-%m-%d_%H-%M-%S')
    
    # Definer tidsvinduet for sammenligning (+/- 2 minutter)
    time_window_start = timestamp2 - timedelta(minutes=2)
    time_window_end = timestamp2 + timedelta(minutes=2)

    # Definer buffer for bredde- og lengdegrad
    lat_buffer = 0.003
    lon_buffer = 0.04

    # Åpne AIS-datafilen og søk etter en linje som matcher tidsstempel og posisjon
    with open("/home/pb/Kafka/kafka_2.13-3.6.0/Innhenting_Konvertering/processed_ais_data.txt", "r") as f:
        for line in f:
            data = ast.literal_eval(line)
            ais_time = datetime.strptime(data.get('timestamp', ''), '%Y-%m-%d_%H-%M-%S')
            ais_latitude = data.get('y', None)
            ais_longitude = data.get('x', None)

            # Sjekk om AIS-tidspunktet og koordinatene er innenfor tidsvinduet og toleransen
            if (time_window_start <= ais_time <= time_window_end and
                (latitude - lat_buffer) <= ais_latitude <= (latitude + lat_buffer) and
                (longitude - lon_buffer) <= ais_longitude <= (longitude + lon_buffer)):
                mmsi = data.get('mmsi', None)
                #name = data.get('name', None)  # Anta at AIS-data inneholder et skipsnavn
                #vessel_type = data.get('vessel_type', None)  # Anta at AIS-data inneholder fartøytype
                matched_data = {
                    "ais_time": ais_time,
                    "mmsi": mmsi,
                    "from_camera": False,
                    "from_ais": True,
                    "ais_latitude": ais_latitude,
                    "ais_longitude": ais_longitude
                }
                print("Ship details from AIS: Match found")  # legger til utskrift for debugging
                return matched_data
    
    # Returner None-verdier og from_camera=True hvis ingen match i AIS-dataen
    print("Ship details from AIS: No match found")  # legger til utskrift for debugging
    return {
        "ais_time": None,
        "mmsi": None,
        "from_camera": True,
        "from_ais": False,
        "ais_latitude": None,
        "ais_longitude": None
    }

# Funksjon for å opprette databasen og tabellen hvis de ikke eksisterer
def create_database():
    with sqlite3.connect(DATABASE) as con:
        cur = con.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS SHIPS (
                timestamp TEXT,
                mmsi INT,
                from_camera BOOLEAN,
                from_ais BOOLEAN,
                image_path TEXT,
                confidence REAL,
                box_coords TEXT,
                latitude REAL,
                longitude REAL
            )
        ''')
        con.commit()

# Funksjon for å lagre skipdata til databasen
def save_to_db(timestamp, mmsi, from_camera, from_ais, image_path, confidence, box_coords, latitude, longitude):
    print("save_to_db: Saving data...")
    with sqlite3.connect(DATABASE) as con:
        cur = con.cursor()
        cur.execute('''
            INSERT INTO SHIPS (timestamp, mmsi, from_camera, from_ais, image_path, confidence, box_coords, latitude, longitude) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, mmsi, from_camera, from_ais, image_path, confidence, box_coords, latitude, longitude))
        con.commit()
    print("save_to_db: Data saved.")  # legger til utskrift etter lagring 
                        
def process_new_directory(new_directory_path):
    print(f"Handling new directory: {new_directory_path}")
    
    # Vent litt for å sikre at alle filer er ferdig skrevet til den nye mappen
    time.sleep(1)
    
    print("Files in directory:", os.listdir(new_directory_path))
    # Finn alle .txt-filer i den nye mappen. Vi antar det bare er én.
    for file in os.listdir(new_directory_path):
        if file.endswith(".txt"):
            print ("Documented_detection_data.txt found")
            detection_info_path = os.path.join(new_directory_path, file)
            try:
                with open(detection_info_path, 'r') as f:
                    for line in f:
                        parsed_line = extract_ship_data(line)
                        if parsed_line:
                            # Her antar vi at bildene ligger i samme mappe som tekstfilen
                            image_path = new_directory_path
                            confidence = parsed_line["confidence"]
                            box_coords = str(parsed_line["box_coords"])  # Konverterer til streng for lagring

                            ais_data = get_ship_details_from_AIS(parsed_line["timestamp"], parsed_line["latitude"], parsed_line["longitude"])
                            if ais_data["from_ais"]:
                                # Bruk dataene fra AIS for å lagre i databasen
                                save_to_db(
                                    ais_data["ais_time"], ais_data["mmsi"], ais_data["from_camera"], ais_data["from_ais"], image_path, 
                                    confidence, box_coords, ais_data["ais_latitude"], ais_data["ais_longitude"]
                                )
                            else:
                                # Lagre dataene som detektert fra kameraet
                                save_to_db(
                                    parsed_line["timestamp"], None, True, False, image_path, 
                                    confidence, box_coords, parsed_line["latitude"], parsed_line["longitude"]
                                )
                break  # Slutt å lete etter .txt-filer etter at den første er funnet og behandlet
            except Exception as e:
                print(f"En feil oppstod under behandling av filen: {e}")

class Watcher:
    DIRECTORY_TO_WATCH = "/home/pb/Kafka/kafka_2.13-3.6.0/Sammnefatning_Lagring/received_data"

    def __init__(self):
        self.observer = Observer()

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except:
            self.observer.stop()
            print("Observer Stopped")

        self.observer.join()

class Handler(FileSystemEventHandler):

    @staticmethod
    def on_created(event):
      if event.is_directory and event.event_type == 'created':
          print(f"Directory from objectdetection received: {event.src_path}")
          process_new_directory(event.src_path)

if __name__ == '__main__':
    create_database()
    w = Watcher()
    w.run()
    
    
