"""Kommandozeilenoberfläche für die Nur.physio Buchhaltung."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
import typer

from .invoice import save_invoice_text
from .repository import InvoiceItem, Repository

app = typer.Typer(help="Verwalten Sie Filialen, Kunden, Leistungen und Rechnungen.")


class AppState:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path
        self.repo = Repository(db_path)


@app.callback()
def main(ctx: typer.Context, db: Optional[Path] = typer.Option(None, help="Pfad zur SQLite-Datenbank.")) -> None:
    """Initialisiert den Applikationszustand."""
    ctx.obj = AppState(db)


@app.command("init-db")
def init_db(ctx: typer.Context) -> None:
    """Stellt sicher, dass die Datenbanktabellen existieren."""
    _ = ctx.obj.repo
    typer.echo("Datenbank erfolgreich initialisiert.")


@app.command()
def add_branch(
    ctx: typer.Context,
    name: str = typer.Option(..., prompt=True, help="Name der Filiale."),
    street: Optional[str] = typer.Option(None, help="Straße"),
    postal_code: Optional[str] = typer.Option(None, help="Postleitzahl"),
    city: Optional[str] = typer.Option(None, help="Ort"),
    email: Optional[str] = typer.Option(None, help="E-Mail-Adresse"),
    phone: Optional[str] = typer.Option(None, help="Telefonnummer"),
) -> None:
    branch = ctx.obj.repo.create_branch(name, street, postal_code, city, email, phone)
    typer.echo(f"Filiale '{branch.name}' (ID {branch.id}) angelegt.")


@app.command()
def list_branches(ctx: typer.Context) -> None:
    """Listet alle verfügbaren Filialen auf."""
    branches = ctx.obj.repo.list_branches()
    if not branches:
        typer.echo("Keine Filialen vorhanden. Legen Sie mit 'add-branch' eine an.")
        return
    for branch in branches:
        typer.echo(f"[{branch.id}] {branch.name} – {branch.city or '-'}")


@app.command()
def add_customer(
    ctx: typer.Context,
    first_name: str = typer.Option(..., prompt=True, help="Vorname"),
    last_name: str = typer.Option(..., prompt=True, help="Nachname"),
    email: Optional[str] = typer.Option(None, help="E-Mail"),
    phone: Optional[str] = typer.Option(None, help="Telefon"),
    street: Optional[str] = typer.Option(None, help="Straße"),
    postal_code: Optional[str] = typer.Option(None, help="Postleitzahl"),
    city: Optional[str] = typer.Option(None, help="Ort"),
) -> None:
    customer = ctx.obj.repo.create_customer(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        street=street,
        postal_code=postal_code,
        city=city,
    )
    typer.echo(f"Kunde {customer.first_name} {customer.last_name} (ID {customer.id}) angelegt.")


@app.command()
def list_customers(ctx: typer.Context) -> None:
    customers = ctx.obj.repo.list_customers()
    if not customers:
        typer.echo("Keine Kunden vorhanden. Nutzen Sie 'add-customer'.")
        return
    for customer in customers:
        typer.echo(f"[{customer.id}] {customer.last_name}, {customer.first_name}")


@app.command()
def add_service(
    ctx: typer.Context,
    name: str = typer.Option(..., prompt=True, help="Bezeichnung der Leistung"),
    unit_price: float = typer.Option(..., prompt=True, help="Preis in EUR"),
    code: Optional[str] = typer.Option(None, help="Positions-/Leistungsnummer"),
    description: Optional[str] = typer.Option(None, help="Beschreibung"),
) -> None:
    service = ctx.obj.repo.create_service(name=name, unit_price=unit_price, code=code, description=description)
    typer.echo(f"Leistung '{service.name}' (ID {service.id}) gespeichert.")


@app.command()
def list_services(ctx: typer.Context) -> None:
    services = ctx.obj.repo.list_services()
    if not services:
        typer.echo("Keine Leistungen vorhanden. Importieren Sie diese oder legen Sie sie mit 'add-service' an.")
        return
    for service in services:
        identifier = service.code or service.id
        typer.echo(f"[{identifier}] {service.name} – {service.unit_price:.2f} €")


@app.command()
def import_services(
    ctx: typer.Context,
    excel_file: Path = typer.Argument(..., exists=True, readable=True, help="Pfad zur Excel-Datei"),
    sheet_name: Optional[str] = typer.Option(None, help="Arbeitsblattname"),
) -> None:
    dataframe = pd.read_excel(excel_file, sheet_name=sheet_name)
    count = ctx.obj.repo.upsert_services_from_dataframe(dataframe)
    typer.echo(f"{count} Leistungen wurden importiert oder aktualisiert.")


def _choose_branch(ctx: typer.Context) -> int:
    branches = ctx.obj.repo.list_branches()
    if not branches:
        raise typer.BadParameter("Es existieren noch keine Filialen. Legen Sie zuerst welche an.")
    typer.echo("Verfügbare Filialen:")
    for branch in branches:
        typer.echo(f"[{branch.id}] {branch.name} ({branch.city or '-'})")
    branch_id = typer.prompt("Filial-ID", type=int)
    if not any(branch.id == branch_id for branch in branches):
        raise typer.BadParameter(f"Filial-ID {branch_id} ist ungültig.")
    return branch_id


def _choose_customer(ctx: typer.Context) -> int:
    customers = ctx.obj.repo.list_customers()
    if not customers:
        raise typer.BadParameter("Es existieren noch keine Kunden. Legen Sie zuerst welche an.")
    typer.echo("Verfügbare Kunden:")
    for customer in customers:
        typer.echo(f"[{customer.id}] {customer.last_name}, {customer.first_name}")
    customer_id = typer.prompt("Kunden-ID", type=int)
    if not any(customer.id == customer_id for customer in customers):
        raise typer.BadParameter(f"Kunden-ID {customer_id} ist ungültig.")
    return customer_id


def _collect_invoice_items(ctx: typer.Context) -> list[InvoiceItem]:
    items: list[InvoiceItem] = []
    typer.echo("Fügen Sie Leistungen hinzu. Lassen Sie den Namen leer, um zu beenden.")
    typer.echo("Sie können nach Name, Leistungsnummer oder ID suchen.")
    while True:
        name_or_code = typer.prompt("Leistung oder Nummer", default="")
        if not name_or_code:
            break
        service = ctx.obj.repo.find_service(name_or_code)
        if service is None:
            typer.echo("Leistung nicht gefunden. Bitte geben Sie Details ein, um sie zu speichern.")
            service_name = name_or_code
            code = typer.prompt("Leistungsnummer", default="") or None
            unit_price = typer.prompt("Preis in EUR", type=float)
            description = typer.prompt("Beschreibung", default="") or None
            service = ctx.obj.repo.create_service(
                name=service_name,
                unit_price=unit_price,
                code=code,
                description=description,
            )
            typer.echo(f"Leistung '{service.name}' gespeichert.")
        quantity = typer.prompt("Menge", type=float)
        items.append(InvoiceItem(service=service, quantity=quantity, unit_price=service.unit_price))
    if not items:
        raise typer.BadParameter("Es wurden keine Leistungen erfasst.")
    return items


@app.command("create-invoice")
def create_invoice(
    ctx: typer.Context,
    issue_date: Optional[str] = typer.Option(None, help="Rechnungsdatum (YYYY-MM-DD)"),
    due_in_days: int = typer.Option(14, help="Zahlungsziel in Tagen"),
    notes: Optional[str] = typer.Option(None, help="Zusätzliche Hinweise"),
    export: bool = typer.Option(True, help="Erzeugt eine Textdatei der Rechnung."),
    output_dir: Optional[Path] = typer.Option(None, help="Ordner für Rechnungsdokumente"),
) -> None:
    branch_id = _choose_branch(ctx)
    customer_id = _choose_customer(ctx)
    items = _collect_invoice_items(ctx)

    parsed_issue_date = date.fromisoformat(issue_date) if issue_date else None
    due_date = (
        parsed_issue_date + pd.Timedelta(days=due_in_days)  # type: ignore[arg-type]
        if parsed_issue_date
        else None
    )

    invoice = ctx.obj.repo.create_invoice(
        branch_id=branch_id,
        customer_id=customer_id,
        items=items,
        issue_date=parsed_issue_date,
        due_date=due_date.date() if due_date else None,
        notes=notes,
    )

    typer.echo(f"Rechnung {invoice.invoice_number} erstellt. Gesamtbetrag: {invoice.total:.2f} €")

    if export:
        path = save_invoice_text(invoice, output_dir=output_dir)
        typer.echo(f"Rechnungsdokument gespeichert unter: {path}")


@app.command()
def list_invoices(ctx: typer.Context) -> None:
    invoices = ctx.obj.repo.list_invoices()
    if not invoices:
        typer.echo("Keine Rechnungen vorhanden.")
        return
    for invoice in invoices:
        typer.echo(
            f"[{invoice.id}] {invoice.invoice_number} – {invoice.customer.last_name} "
            f"({invoice.issue_date.isoformat()}) {invoice.total:.2f} €"
        )


def run() -> None:
    app()


if __name__ == "__main__":
    run()
