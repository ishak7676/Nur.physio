"""Hilfsfunktionen zum Erstellen von Rechnungsausgaben."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Optional

from .repository import Invoice


def format_address(name: str, street: Optional[str], postal_code: Optional[str], city: Optional[str]) -> str:
    lines = [name]
    if street:
        lines.append(street)
    address_line = " ".join(filter(None, [postal_code, city]))
    if address_line:
        lines.append(address_line)
    return "\n".join(lines)


def render_invoice_text(invoice: Invoice) -> str:
    branch_name = invoice.branch.name
    branch_address = format_address(
        branch_name,
        invoice.branch.street,
        invoice.branch.postal_code,
        invoice.branch.city,
    )
    customer_name = f"{invoice.customer.first_name} {invoice.customer.last_name}"
    customer_address = format_address(
        customer_name,
        invoice.customer.street,
        invoice.customer.postal_code,
        invoice.customer.city,
    )

    items_lines = ["Leistung                          Menge    Einzelpreis    Gesamt"]
    items_lines.append("-" * 70)
    for item in invoice.items:
        name = item.service.name[:30].ljust(30)
        qty = f"{item.quantity:.2f}".rjust(8)
        unit_price = f"{item.unit_price:.2f} €".rjust(15)
        total = f"{item.line_total:.2f} €".rjust(10)
        items_lines.append(f"{name}{qty}{unit_price}{total}")

    items_lines.append("-" * 70)
    items_lines.append(f"Gesamtbetrag: {invoice.total:.2f} €")

    notes = invoice.notes or """Bitte überweisen Sie den offenen Betrag innerhalb von 14 Tagen."""

    items_text = "\n".join(items_lines)

    text = dedent(
        f"""
        {branch_address}

        Rechnung: {invoice.invoice_number}
        Datum: {invoice.issue_date.isoformat()}
        Fällig am: {invoice.due_date.isoformat()}

        Empfänger:
        {customer_address}

        {items_text}

        Hinweis:
        {notes}

        Erstellt am {datetime.now().strftime('%d.%m.%Y %H:%M')}.
        """
    ).strip()

    return text


def save_invoice_text(invoice: Invoice, output_dir: Optional[Path] = None) -> Path:
    output_dir = Path(output_dir) if output_dir else Path.cwd() / "invoices"
    output_dir.mkdir(parents=True, exist_ok=True)
    invoice_path = output_dir / f"{invoice.invoice_number}.txt"
    invoice_path.write_text(render_invoice_text(invoice), encoding="utf-8")
    return invoice_path
