"""Datenbank-Utilities für das Nur.physio Rechnungswerkzeug."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional

DEFAULT_DB_PATH = Path.home() / ".nur_physio" / "nur_physio.db"


def ensure_database_directory(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Erstellt eine SQLite-Verbindung und sorgt für das Datenbank-Verzeichnis."""
    resolved_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    ensure_database_directory(resolved_path)
    connection = sqlite3.connect(resolved_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path: Optional[Path] = None) -> None:
    """Legt alle benötigten Tabellen an, sofern sie noch nicht existieren."""
    with get_connection(db_path) as connection:
        cursor = connection.cursor()
        cursor.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS branches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                street TEXT,
                postal_code TEXT,
                city TEXT,
                email TEXT,
                phone TEXT
            );

            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                street TEXT,
                postal_code TEXT,
                city TEXT
            );

            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                name TEXT NOT NULL,
                description TEXT,
                unit_price REAL NOT NULL,
                UNIQUE(code),
                UNIQUE(name)
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL UNIQUE,
                branch_id INTEGER NOT NULL REFERENCES branches(id),
                customer_id INTEGER NOT NULL REFERENCES customers(id),
                issue_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
                service_id INTEGER NOT NULL REFERENCES services(id),
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                line_total REAL NOT NULL
            );
            """
        )
        connection.commit()


def iter_rows(cursor: sqlite3.Cursor) -> Iterable[sqlite3.Row]:
    """Hilfsfunktion, um Cursor-Ergebnisse zu iterieren."""
    row = cursor.fetchone()
    while row is not None:
        yield row
        row = cursor.fetchone()
