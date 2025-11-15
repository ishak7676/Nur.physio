# Nur.physio Buchhaltungs- und Rechnungsprogramm

Dieses Projekt stellt eine leichtgewichtige Kommandozeilen-Anwendung bereit, mit der Sie
Filialen, Kunden, Leistungen und private Rechnungen für Ihre Physiotherapie-Praxis
verwalten können. Die Daten werden in einer SQLite-Datenbank gespeichert und Rechnungen
können als Textdateien exportiert werden.

## Voraussetzungen

* Python 3.10 oder neuer
* Abhängigkeiten aus `requirements.txt`

Installieren Sie die Pakete beispielsweise mit:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Erste Schritte

Initialisieren Sie die Datenbank und legen Sie erste Stammdaten an:

```bash
python -m nur_physio init-db
python -m nur_physio add-branch --name "Praxis Wedding" --street "Musterstraße 1" --postal-code 13353 --city Berlin
python -m nur_physio add-customer --first-name Max --last-name Müller --email max.mueller@example.com
```

Leistungen können entweder manuell erfasst werden …

```bash
python -m nur_physio add-service --name "Krankengymnastik" --unit-price 45.0 --code KG123
```

… oder aus einer vorhandenen Excel-Datei importiert werden. Erwartet werden mindestens
Spalten für Name und Preis (z. B. `Leistung` und `Preis`). Optionale Spalten sind
Leistungsnummer (`Code`) und Beschreibung.

```bash
python -m nur_physio import-services leistungen.xlsx
```

## Rechnungen erstellen

Starten Sie den interaktiven Rechnungserstellungsprozess mit:

```bash
python -m nur_physio create-invoice
```

Sie wählen dabei die Filiale, den Kunden sowie die abzurechnenden Leistungen aus.
Nicht vorhandene Leistungen können direkt angelegt und gespeichert werden. Nach dem
Abschluss wird die Rechnung inklusive Zahlungsziel gespeichert und als Textdatei im
Ordner `invoices/` abgelegt.

Bereits angelegte Rechnungen lassen sich über

```bash
python -m nur_physio list-invoices
```

einsehen.

## Datenablage

Standardmäßig werden alle Daten in `~/.nur_physio/nur_physio.db` gespeichert. Über den
Parameter `--db` können Sie einen anderen Speicherort angeben, z. B. für Tests oder
mehrere Umgebungen:

```bash
python -m nur_physio --db data/test.db init-db
```

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Weitere Details finden Sie in der Datei
[`LICENSE`](LICENSE), sofern vorhanden.
