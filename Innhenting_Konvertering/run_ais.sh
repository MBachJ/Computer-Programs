#!/bin/bash

# Starter netcat for å motta AIS-data
nc 153.44.253.27 5631 > ais_data.txt &

# Venter noen sekunder for å starte og samle litt data
sleep 10

# Kontinuerlig dekoder AIS-meldinger
while true; do
    python3 decode_ais.py  # Kjører Python-scriptet for å dekode AIS-data
    sleep 5  # Venter i 5 sekunder før scriptet kjøres på nytt
done

