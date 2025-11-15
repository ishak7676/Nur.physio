"""Weboberfläche für das Nur.physio Rechnungswesen."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .repository import InvoiceItem, Repository

DB_ENV_VAR = "NUR_PHYSIO_DB_PATH"


def _get_db_path() -> Optional[Path]:
    raw = os.environ.get(DB_ENV_VAR)
    return Path(raw) if raw else None


def get_repository() -> Repository:
    return Repository(_get_db_path())


def _optional(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _parse_date(value: Optional[str]) -> Optional[date]:
    value = _optional(value)
    if not value:
        return None
    return date.fromisoformat(value)


app = FastAPI(title="Nur.physio Web")

_templates = Jinja2Templates(directory=str(Path(__file__).parent / "web" / "templates"))
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "web" / "static")),
    name="static",
)


@app.middleware("http")
async def add_common_context(request, call_next):  # type: ignore[override]
    response = await call_next(request)
    return response


@app.get("/")
async def dashboard(request: Request, repo: Repository = Depends(get_repository)):
    branches = repo.list_branches()
    customers = repo.list_customers()
    services = repo.list_services()
    invoices = repo.list_invoices()
    return _templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "branch_count": len(branches),
            "customer_count": len(customers),
            "service_count": len(services),
            "invoice_count": len(invoices),
        },
    )


@app.get("/branches")
async def list_branches(request: Request, repo: Repository = Depends(get_repository)):
    branches = repo.list_branches()
    return _templates.TemplateResponse(
        "branches.html",
        {"request": request, "branches": branches},
    )


@app.post("/branches")
async def create_branch(
    repo: Repository = Depends(get_repository),
    name: str = Form(...),
    street: Optional[str] = Form(None),
    postal_code: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
):
    repo.create_branch(
        name=name,
        street=_optional(street),
        postal_code=_optional(postal_code),
        city=_optional(city),
        email=_optional(email),
        phone=_optional(phone),
    )
    return RedirectResponse("/branches", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/customers")
async def list_customers(request: Request, repo: Repository = Depends(get_repository)):
    customers = repo.list_customers()
    return _templates.TemplateResponse(
        "customers.html",
        {"request": request, "customers": customers},
    )


@app.post("/customers")
async def create_customer(
    repo: Repository = Depends(get_repository),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    street: Optional[str] = Form(None),
    postal_code: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
):
    repo.create_customer(
        first_name=first_name,
        last_name=last_name,
        email=_optional(email),
        phone=_optional(phone),
        street=_optional(street),
        postal_code=_optional(postal_code),
        city=_optional(city),
    )
    return RedirectResponse("/customers", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/services")
async def list_services(request: Request, repo: Repository = Depends(get_repository)):
    services = repo.list_services()
    return _templates.TemplateResponse(
        "services.html",
        {"request": request, "services": services},
    )


@app.post("/services")
async def create_service(
    repo: Repository = Depends(get_repository),
    name: str = Form(...),
    unit_price: float = Form(...),
    code: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
):
    repo.create_service(
        name=name,
        unit_price=unit_price,
        code=_optional(code),
        description=_optional(description),
    )
    return RedirectResponse("/services", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/invoices")
async def list_invoices(request: Request, repo: Repository = Depends(get_repository)):
    invoices = repo.list_invoices()
    return _templates.TemplateResponse(
        "invoices.html",
        {"request": request, "invoices": invoices},
    )


@app.get("/invoices/new")
async def invoice_form(request: Request, repo: Repository = Depends(get_repository)):
    branches = repo.list_branches()
    customers = repo.list_customers()
    services = repo.list_services()
    if not branches or not customers or not services:
        return _templates.TemplateResponse(
            "invoice_prerequisites.html",
            {
                "request": request,
                "branches": branches,
                "customers": customers,
                "services": services,
            },
        )
    return _templates.TemplateResponse(
        "invoice_form.html",
        {
            "request": request,
            "branches": branches,
            "customers": customers,
            "services": services,
        },
    )


@app.post("/invoices")
async def create_invoice(request: Request, repo: Repository = Depends(get_repository)):
    form = await request.form()
    try:
        branch_id = int(form["branch_id"])
        customer_id = int(form["customer_id"])
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Ungültige Filiale oder Kunde.") from error

    service_ids = form.getlist("service_id")
    quantities = form.getlist("quantity")
    unit_prices = form.getlist("unit_price")

    items: list[InvoiceItem] = []
    for service_id_raw, quantity_raw, price_raw in zip(service_ids, quantities, unit_prices):
        if not service_id_raw:
            continue
        try:
            service = repo.get_service(int(service_id_raw))
            quantity = float(quantity_raw or 1)
            unit_price = float(price_raw or service.unit_price)
        except (ValueError, KeyError) as error:
            raise HTTPException(status_code=400, detail="Ungültige Leistungsdaten.") from error
        items.append(InvoiceItem(service=service, quantity=quantity, unit_price=unit_price))

    if not items:
        raise HTTPException(status_code=400, detail="Es muss mindestens eine Leistung angegeben werden.")

    issue_date = _parse_date(form.get("issue_date"))
    due_date = _parse_date(form.get("due_date"))
    notes = _optional(form.get("notes"))

    invoice = repo.create_invoice(
        branch_id=branch_id,
        customer_id=customer_id,
        items=items,
        issue_date=issue_date,
        due_date=due_date,
        notes=notes,
    )

    return RedirectResponse(f"/invoices/{invoice.id}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/invoices/{invoice_id}")
async def invoice_detail(invoice_id: int, request: Request, repo: Repository = Depends(get_repository)):
    try:
        invoice = repo.get_invoice(invoice_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return _templates.TemplateResponse(
        "invoice_detail.html",
        {"request": request, "invoice": invoice},
    )
