# Vertrags- und Auftragsverwaltung (Python/FastAPI)

Diese FastAPI-Anwendung stellt einen einfachen mehrstufigen Aufbau bereit:

- **Master-Login** verwaltet Firmen und legt Firmen-Admins/Mitarbeitende an.
- **Firmen** verwalten Mitarbeitende, Kund:innen und Aufträge mit Strom-, Gas- oder Telekommunikations-Tarifen.
- **Dynamische Felder** erlauben es, Formulare um eigene Eingaben (z. B. weitere Kundendaten) zu erweitern.
- **Dashboard** listet die Verträge mit dem nächsten Enddatum firmenübergreifend bzw. firmenbezogen.

## Schnellstart

1. Abhängigkeiten installieren und Server starten:

   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. Beim ersten Start wird automatisch ein Master-Nutzer angelegt:

   - Nutzername: `master`
   - Passwort: `changeme`

   Hole ein Token über `POST /auth/token` mit `username=master` und `password=changeme`.

## API-Überblick

- **Authentifizierung**
  - `POST /auth/token` – Token holen (OAuth2 Password Flow, Token = Nutzername).
  - `POST /auth/change-password` – eigenes Passwort ändern.

- **Firmen & Mitarbeitende** (nur Master bzw. Company Admin)
  - `POST /companies` – Firma anlegen.
  - `PUT/DELETE /companies/{id}` – Firma pflegen.
  - `POST /companies/{id}/users` – Company-Admins oder Mitarbeitende erstellen.

- **Kund:innen** (Company Admin oder Mitarbeitende der Firma)
  - `POST /companies/{id}/customers` – anlegen mit Name, Kontaktdaten, IBAN, Geburtsdatum.
  - `PUT/DELETE /customers/{id}` – Daten pflegen/löschen.

- **Aufträge/Tarife** (Company Admin oder Mitarbeitende der Firma)
  - `POST /companies/{id}/orders` – Auftrag inkl. Auftragsnummer, Tariftyp (Strom, Gas, Telekom), Anbieter, Kundennummern, Zählernummern, Telekom-Art (Mobil/Festnetz), Vertragslaufzeit, Kündigungsdatum und Kennzeichen „Bestandvertrag“ erfassen.
  - `PUT/DELETE /orders/{id}` – Auftrag anpassen oder löschen.
  - `GET /dashboard/expiring` – sortierte Liste der nächst auslaufenden Verträge.
  - `GET /orders/by-user/{user_id}` – Aufträge eines Mitarbeitenden.

- **Dynamische Formularfelder**
  - `POST /custom-fields` – neues Feld-Template für `customer` oder `order` anlegen (z. B. weitere Pflichtfelder).
  - `GET /custom-fields` – Feld-Templates auflisten.
  - `POST /custom-field-values` – Werte für ein Feld bei einer Entität setzen.
  - `GET /custom-field-values/{entity_type}/{entity_id}` – alle Zusatzwerte lesen.

## Hinweise

- Alle geschützten Endpunkte erfordern das Bearer-Token im `Authorization`-Header.
- SQLite (`app.db`) wird automatisch erstellt. Für einen produktiven Einsatz können Engine-URL und Authentifizierung leicht erweitert werden.
