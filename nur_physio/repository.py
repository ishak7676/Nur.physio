"""Datenzugriffsschicht für das Nur.physio Rechnungswerkzeug."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from .database import get_connection, initialize_database, iter_rows


@dataclass
class Branch:
    id: int
    name: str
    street: Optional[str]
    postal_code: Optional[str]
    city: Optional[str]
    email: Optional[str]
    phone: Optional[str]


@dataclass
class Customer:
    id: int
    first_name: str
    last_name: str
    email: Optional[str]
    phone: Optional[str]
    street: Optional[str]
    postal_code: Optional[str]
    city: Optional[str]


@dataclass
class Service:
    id: int
    code: Optional[str]
    name: str
    description: Optional[str]
    unit_price: float


@dataclass
class InvoiceItem:
    service: Service
    quantity: float
    unit_price: float

    @property
    def line_total(self) -> float:
        return round(self.quantity * self.unit_price, 2)


@dataclass
class Invoice:
    id: int
    invoice_number: str
    branch: Branch
    customer: Customer
    issue_date: date
    due_date: date
    notes: Optional[str]
    items: Sequence[InvoiceItem]

    @property
    def total(self) -> float:
        return round(sum(item.line_total for item in self.items), 2)


class Repository:
    """Bündelt alle Datenbankzugriffe."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path
        initialize_database(db_path)

    # --- Branches -----------------------------------------------------
    def create_branch(
        self,
        name: str,
        street: Optional[str] = None,
        postal_code: Optional[str] = None,
        city: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Branch:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO branches (name, street, postal_code, city, email, phone)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, street, postal_code, city, email, phone),
            )
            connection.commit()
            branch_id = cursor.lastrowid
        return self.get_branch(branch_id)

    def get_branch(self, branch_id: int) -> Branch:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                "SELECT * FROM branches WHERE id = ?", (branch_id,)
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Filiale mit ID {branch_id} nicht gefunden.")
            return Branch(**row)

    def list_branches(self) -> List[Branch]:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute("SELECT * FROM branches ORDER BY name")
            return [Branch(**row) for row in iter_rows(cursor)]

    # --- Customers ----------------------------------------------------
    def create_customer(
        self,
        first_name: str,
        last_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        street: Optional[str] = None,
        postal_code: Optional[str] = None,
        city: Optional[str] = None,
    ) -> Customer:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO customers (first_name, last_name, email, phone, street, postal_code, city)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (first_name, last_name, email, phone, street, postal_code, city),
            )
            connection.commit()
            customer_id = cursor.lastrowid
        return self.get_customer(customer_id)

    def get_customer(self, customer_id: int) -> Customer:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                "SELECT * FROM customers WHERE id = ?",
                (customer_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Kunde mit ID {customer_id} nicht gefunden.")
            return Customer(**row)

    def list_customers(self) -> List[Customer]:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                "SELECT * FROM customers ORDER BY last_name, first_name"
            )
            return [Customer(**row) for row in iter_rows(cursor)]

    # --- Services -----------------------------------------------------
    def create_service(
        self,
        name: str,
        unit_price: float,
        code: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Service:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO services (name, unit_price, code, description)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET unit_price = excluded.unit_price,
                                            code = COALESCE(excluded.code, services.code),
                                            description = COALESCE(excluded.description, services.description)
                """,
                (name, unit_price, code, description),
            )
            connection.commit()
            service_id = cursor.lastrowid or self.get_service_by_name(name).id
        return self.get_service(service_id)

    def get_service(self, service_id: int) -> Service:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                "SELECT * FROM services WHERE id = ?",
                (service_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Leistung mit ID {service_id} nicht gefunden.")
            return Service(**row)

    def get_service_by_name(self, name: str) -> Service:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                "SELECT * FROM services WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Leistung '{name}' nicht gefunden.")
            return Service(**row)

    def find_service(self, keyword: str) -> Optional[Service]:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                "SELECT * FROM services WHERE name = ? OR code = ?",
                (keyword, keyword),
            )
            row = cursor.fetchone()
            return Service(**row) if row else None

    def list_services(self) -> List[Service]:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute("SELECT * FROM services ORDER BY name")
            return [Service(**row) for row in iter_rows(cursor)]

    # --- Invoices -----------------------------------------------------
    def create_invoice(
        self,
        branch_id: int,
        customer_id: int,
        items: Sequence[InvoiceItem],
        issue_date: Optional[date] = None,
        due_date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> Invoice:
        issue_date = issue_date or date.today()
        due_date = due_date or issue_date + timedelta(days=14)

        with get_connection(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM invoices")
            next_id = cursor.fetchone()[0]
            invoice_number = f"INV-{next_id:05d}"
            cursor.execute(
                """
                INSERT INTO invoices (invoice_number, branch_id, customer_id, issue_date, due_date, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_number,
                    branch_id,
                    customer_id,
                    issue_date.isoformat(),
                    due_date.isoformat(),
                    notes,
                ),
            )
            invoice_id = cursor.lastrowid

            for item in items:
                cursor.execute(
                    """
                    INSERT INTO invoice_items (invoice_id, service_id, quantity, unit_price, line_total)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        invoice_id,
                        item.service.id,
                        item.quantity,
                        item.unit_price,
                        item.line_total,
                    ),
                )

            connection.commit()

        return self.get_invoice(invoice_id)

    def get_invoice(self, invoice_id: int) -> Invoice:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Rechnung mit ID {invoice_id} nicht gefunden.")
            branch = self.get_branch(row["branch_id"])
            customer = self.get_customer(row["customer_id"])
            items = self.get_invoice_items(invoice_id)
            return Invoice(
                id=row["id"],
                invoice_number=row["invoice_number"],
                branch=branch,
                customer=customer,
                issue_date=date.fromisoformat(row["issue_date"]),
                due_date=date.fromisoformat(row["due_date"]),
                notes=row["notes"],
                items=items,
            )

    def get_invoice_items(self, invoice_id: int) -> List[InvoiceItem]:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                SELECT services.*, invoice_items.quantity, invoice_items.unit_price
                FROM invoice_items
                JOIN services ON services.id = invoice_items.service_id
                WHERE invoice_items.invoice_id = ?
                ORDER BY services.name
                """,
                (invoice_id,),
            )
            items: List[InvoiceItem] = []
            for row in iter_rows(cursor):
                service = Service(
                    id=row["id"],
                    code=row["code"],
                    name=row["name"],
                    description=row["description"],
                    unit_price=row["unit_price"],
                )
                items.append(
                    InvoiceItem(
                        service=service,
                        quantity=row["quantity"],
                        unit_price=row["unit_price"],
                    )
                )
            return items

    def list_invoices(self) -> List[Invoice]:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute("SELECT id FROM invoices ORDER BY issue_date DESC")
            invoice_ids = [row["id"] for row in iter_rows(cursor)]
        return [self.get_invoice(invoice_id) for invoice_id in invoice_ids]

    # --- Import -------------------------------------------------------
    def upsert_services_from_dataframe(self, dataframe) -> int:
        """Legt Leistungen aus einem DataFrame an oder aktualisiert sie.

        Erwartet Spaltennamen wie ``name`` oder ``Leistung`` für die Bezeichnung,
        ``code`` oder ``Leistungsnummer`` sowie ``unit_price`` oder ``Preis``.
        """

        column_mapping = {
            "name": {"name", "leistung", "leistungsname", "bezeichnung"},
            "code": {"code", "leistungsnummer", "positionsnummer"},
            "unit_price": {"unit_price", "preis", "betrag"},
            "description": {"description", "beschreibung", "notiz"},
        }

        def resolve(column_group: set[str]) -> Optional[str]:
            for candidate in dataframe.columns:
                if candidate.strip().lower() in column_group:
                    return candidate
            return None

        name_column = resolve(column_mapping["name"])
        price_column = resolve(column_mapping["unit_price"])
        code_column = resolve(column_mapping["code"])
        description_column = resolve(column_mapping["description"])

        if not name_column or not price_column:
            raise ValueError(
                "Die Excel-Datei muss mindestens Spalten für Name und Preis enthalten."
            )

        created = 0
        for _, row in dataframe.iterrows():
            name = str(row[name_column]).strip()
            if not name:
                continue
            price = float(row[price_column])
            code = str(row[code_column]).strip() if code_column else None
            description = (
                str(row[description_column]).strip() if description_column else None
            )
            self.create_service(name=name, unit_price=price, code=code or None, description=description or None)
            created += 1
        return created


__all__ = [
    "Repository",
    "Branch",
    "Customer",
    "Service",
    "Invoice",
    "InvoiceItem",
]
