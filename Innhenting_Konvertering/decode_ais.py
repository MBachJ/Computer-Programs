import ais  # Importerer AIS (Automatic Identification System) dekoder bibliotek
import sys
import os
import datetime  # Bibliotek for å håndtere dato og tid

# Import numpy for polygon operations
import numpy as np

from matplotlib import path as mpl_path


# Definer polygonkoordinatene for det nye området
polygon = np.array([
    [60.3949255062713, 5.269844802679123],
    [60.404823680695, 5.314547345232413],
    [60.41757266054785, 5.2629082012484405],
    [60.395877384615666, 5.260596000771546]
])

def is_within_bounds(lat, lon):
    """Sjekker om den er innefor området basert på lat, lon"""
    return mpl_path.Path(polygon).contains_point((lat, lon))

# Funksjon for å tømme innholdet i en fil
def clear_file_content(filename):
    """Tøm innholdet av filen."""
    with open(filename, 'w'):
        pass  # Åpner filen i skrivemodus og tømmer innholdet uten å skrive noe.

# Funksjon for å sjekke og tømme filen hvis størrelsen overskrider max_size_mb
def check_and_clear_file(filename, max_size_mb=10):
    """Tøm innholdet av filen hvis størrelsen overskrider max_size_mb."""
    file_size_mb = os.path.getsize(filename) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        clear_file_content(filename)

def main():
    # Definerer filnavnene som skal brukes for inndata, bearbeidede data og feilmeldinger
    input_filename = 'ais_data.txt'
    processed_filename = 'processed_ais_data.txt'
    failed_filename = 'failed_decoding.txt'
    
    # Sjekker og tømmer inndatafilen hvis den er for stor før nye meldinger legges til
    check_and_clear_file(input_filename)

    # Oppretter et sett for å holde styr på hvilke meldingstyper som er oppdaget
    message_types_encountered = set()

    # Åpner inndatafilen og leser linjene
    with open(input_filename, 'r') as f:
        lines = f.readlines()

    # Initialiserer tellere for meldinger
    relevant_message_count = 0
    failed_message_count = 0
    total_messages = len(lines)

    # Åpner filer for bearbeidede data og feil for skriving
    with open(processed_filename, 'a') as p_file, open(failed_filename, 'w') as f_file:
        for line in lines:
            # Sjekker om linjen inneholder en AIS-melding og ekstraherer den
            if line.startswith("\\s:") and '!BSVDM' in line:
                line = line.split('!BSVDM')[1]
                line = '!BSVDM' + line
            
            try:
                # Dekoder AIS-meldingen
                msg = ais.decode(line.strip().split(',')[5], 0)
                message_type = msg['id']
                message_types_encountered.add(message_type)

                # Sjekker om meldingen er av en relevant type og inneholder nødvendige koordinater
                if message_type in [1, 2, 3, 5, 18, 19, 24] and 'y' in msg and 'x' in msg:
                    # Runder av koordinatene til tre desimaler
                    msg['y'] = round(msg['y'], 3)
                    msg['x'] = round(msg['x'], 3)

                    # Sjekker om posisjonen er innenfor det definerte området
                    if is_within_bounds(msg['y'], msg['x']):
                        # Henter nåværende tidspunkt og formaterer det
                        current_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                        # Organiserer meldingsdata i ønsket format
                        formatted_msg = {
                            'id': msg['id'],
                            'mmsi': msg.get('mmsi'),  # Henter MMSI-nummeret fra AIS-meldingen
                            'y': msg['y'],
                            'x': msg['x'],
                            'timestamp': current_time
                        }

                        
                        # Skriver den formaterte meldingen til fil
                        p_file.write(str(formatted_msg) + '\n')
                        # Skyller data til filen umiddelbart
                        p_file.flush()
                        relevant_message_count += 1
            except Exception as e:
                # Håndterer eventuelle unntak og logger feilmeldinger
                failed_message_count += 1
                error_msg = f"Line: {line}\nError: {e}\n"
                f_file.write(error_msg)
                f_file.flush()

    # Logger statistikk om prosesseringen
    print(f"Totalt antall meldinger lest: {total_messages}")
    print(f"Relevante meldinger: {relevant_message_count}")
    print(f"Meldinger som feilet: {failed_message_count}")
    print(f"Møtte meldingstyper: {list(message_types_encountered)}")

    # Tømmer inndatafilen etter at prosesseringen er fullført
    clear_file_content(input_filename)

# Kontrollerer om skriptet er hovedprogrammet og kjører i så fall main-funksjonen
if __name__ == '__main__':
    main()

