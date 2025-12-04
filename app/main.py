from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy import Column, String


DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(sa_column=Column("username", String, unique=True, index=True))
    password_hash: str
    role: str
    company_id: Optional[int] = Field(default=None, foreign_key="company.id")


class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    first_name: str
    last_name: str
    birthdate: Optional[date] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    iban: Optional[str] = None


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    customer_id: int = Field(foreign_key="customer.id")
    created_by: int = Field(foreign_key="user.id")
    order_number: str
    contract_type: str  # electricity, gas, telecom
    provider_name: Optional[str] = None
    product_label: Optional[str] = None
    is_existing_contract: bool = False
    customer_number: Optional[str] = None
    meter_number: Optional[str] = None
    telecom_kind: Optional[str] = None  # mobile or landline
    telecom_customer_number: Optional[str] = None
    telecom_phone_number: Optional[str] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    cancellation_date: Optional[date] = None
    tv_pp_number: Optional[str] = None
    cr_mt_number: Optional[str] = None


class CustomFieldDefinition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_type: str  # e.g. customer, order
    name: str
    label: str
    data_type: str = "text"


class CustomFieldValue(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_type: str
    entity_id: int
    definition_id: int = Field(foreign_key="customfielddefinition.id")
    value: str


class UserCreate(SQLModel):
    username: str
    password: str
    role: str
    company_id: Optional[int] = None


class UserUpdatePassword(SQLModel):
    password: str


class CompanyCreate(SQLModel):
    name: str


class CompanyUpdate(SQLModel):
    name: str


class CustomerCreate(SQLModel):
    first_name: str
    last_name: str
    birthdate: Optional[date] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    iban: Optional[str] = None


class CustomerUpdate(CustomerCreate):
    pass


class OrderCreate(SQLModel):
    customer_id: int
    order_number: str
    contract_type: str
    provider_name: Optional[str] = None
    product_label: Optional[str] = None
    is_existing_contract: bool = False
    customer_number: Optional[str] = None
    meter_number: Optional[str] = None
    telecom_kind: Optional[str] = None
    telecom_customer_number: Optional[str] = None
    telecom_phone_number: Optional[str] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    cancellation_date: Optional[date] = None
    tv_pp_number: Optional[str] = None
    cr_mt_number: Optional[str] = None


class OrderUpdate(OrderCreate):
    pass


class CustomFieldDefinitionCreate(SQLModel):
    entity_type: str
    name: str
    label: str
    data_type: str = "text"


class CustomFieldValueCreate(SQLModel):
    entity_type: str
    entity_id: int
    definition_id: int
    value: str


app = FastAPI(title="Vertrags- und Auftragsverwaltung")


def get_session():
    with Session(engine) as session:
        yield session


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    statement = select(User).where(User.username == username)
    return session.exec(statement).first()


def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    user = get_user_by_username(session, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ungültiges Token")
    return user


def require_role(user: User, allowed_roles: List[str], company_id: Optional[int] = None) -> None:
    if user.role == "master":
        return
    if user.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Berechtigung")
    if company_id is not None and user.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Falsches Unternehmen")


@app.on_event("startup")
def on_startup() -> None:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        master_exists = session.exec(select(User).where(User.role == "master")).first()
        if not master_exists:
            master = User(
                username="master",
                password_hash=get_password_hash("changeme"),
                role="master",
            )
            session.add(master)
            session.commit()


@app.post("/auth/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = get_user_by_username(session, form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Falsche Zugangsdaten")
    return {"access_token": user.username, "token_type": "bearer", "role": user.role}


@app.post("/auth/change-password")
def change_password(update: UserUpdatePassword, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    current_user.password_hash = get_password_hash(update.password)
    session.add(current_user)
    session.commit()
    return {"message": "Passwort aktualisiert"}


@app.post("/companies", response_model=Company)
def create_company(company: CompanyCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    require_role(current_user, ["master"], None)
    db_company = Company(name=company.name)
    session.add(db_company)
    session.commit()
    session.refresh(db_company)
    return db_company


@app.get("/companies", response_model=List[Company])
def list_companies(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    require_role(current_user, ["master"], None)
    return session.exec(select(Company)).all()


@app.put("/companies/{company_id}", response_model=Company)
def update_company(company_id: int, company: CompanyUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    require_role(current_user, ["master"], None)
    db_company = session.get(Company, company_id)
    if not db_company:
        raise HTTPException(status_code=404, detail="Unternehmen nicht gefunden")
    db_company.name = company.name
    session.add(db_company)
    session.commit()
    session.refresh(db_company)
    return db_company


@app.delete("/companies/{company_id}")
def delete_company(company_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    require_role(current_user, ["master"], None)
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Unternehmen nicht gefunden")
    session.delete(company)
    session.commit()
    return {"message": "Unternehmen gelöscht"}


@app.post("/companies/{company_id}/users", response_model=User)
def create_user_for_company(company_id: int, user: UserCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    require_role(current_user, ["master", "company_admin"], company_id)
    if user.role not in {"company_admin", "employee"}:
        raise HTTPException(status_code=400, detail="Ungültige Rolle")
    if user.company_id and user.company_id != company_id:
        raise HTTPException(status_code=400, detail="Unternehmens-ID stimmt nicht")
    if get_user_by_username(session, user.username):
        raise HTTPException(status_code=400, detail="Nutzername bereits vergeben")
    db_user = User(
        username=user.username,
        password_hash=get_password_hash(user.password),
        role=user.role,
        company_id=company_id,
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


@app.post("/companies/{company_id}/customers", response_model=Customer)
def create_customer(company_id: int, customer: CustomerCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    require_role(current_user, ["company_admin", "employee"], company_id)
    db_customer = Customer(company_id=company_id, **customer.dict())
    session.add(db_customer)
    session.commit()
    session.refresh(db_customer)
    return db_customer


@app.put("/customers/{customer_id}", response_model=Customer)
def update_customer(customer_id: int, customer: CustomerUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    db_customer = session.get(Customer, customer_id)
    if not db_customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    require_role(current_user, ["company_admin", "employee"], db_customer.company_id)
    for field, value in customer.dict().items():
        setattr(db_customer, field, value)
    session.add(db_customer)
    session.commit()
    session.refresh(db_customer)
    return db_customer


@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    db_customer = session.get(Customer, customer_id)
    if not db_customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    require_role(current_user, ["company_admin"], db_customer.company_id)
    session.delete(db_customer)
    session.commit()
    return {"message": "Kunde gelöscht"}


@app.post("/companies/{company_id}/orders", response_model=Order)
def create_order(company_id: int, order: OrderCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    require_role(current_user, ["company_admin", "employee"], company_id)
    customer = session.get(Customer, order.customer_id)
    if not customer or customer.company_id != company_id:
        raise HTTPException(status_code=400, detail="Kunde gehört nicht zum Unternehmen")
    db_order = Order(company_id=company_id, created_by=current_user.id, **order.dict())
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    return db_order


@app.put("/orders/{order_id}", response_model=Order)
def update_order(order_id: int, order: OrderUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    db_order = session.get(Order, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    require_role(current_user, ["company_admin", "employee"], db_order.company_id)
    for field, value in order.dict().items():
        setattr(db_order, field, value)
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    return db_order


@app.delete("/orders/{order_id}")
def delete_order(order_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    db_order = session.get(Order, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    require_role(current_user, ["company_admin"], db_order.company_id)
    session.delete(db_order)
    session.commit()
    return {"message": "Auftrag gelöscht"}


@app.get("/dashboard/expiring", response_model=List[Order])
def expiring_orders(limit: int = 50, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if current_user.role not in {"master", "company_admin", "employee"}:
        raise HTTPException(status_code=403, detail="Keine Berechtigung")
    statement = select(Order)
    if current_user.role != "master":
        statement = statement.where(Order.company_id == current_user.company_id)
    statement = statement.where(Order.contract_end.is_not(None)).order_by(Order.contract_end)
    results = session.exec(statement.limit(limit)).all()
    return results


@app.get("/orders/by-user/{user_id}", response_model=List[Order])
def orders_by_user(user_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if current_user.role != "master" and current_user.id != user_id:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Nutzer nicht gefunden")
        require_role(current_user, ["company_admin"], user.company_id)
    statement = select(Order).where(Order.created_by == user_id)
    return session.exec(statement).all()


@app.post("/custom-fields", response_model=CustomFieldDefinition)
def create_custom_field(definition: CustomFieldDefinitionCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if current_user.role not in {"master", "company_admin"}:
        raise HTTPException(status_code=403, detail="Keine Berechtigung")
    db_definition = CustomFieldDefinition(**definition.dict())
    session.add(db_definition)
    session.commit()
    session.refresh(db_definition)
    return db_definition


@app.get("/custom-fields", response_model=List[CustomFieldDefinition])
def list_custom_fields(entity_type: Optional[str] = None, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    query = select(CustomFieldDefinition)
    if entity_type:
        query = query.where(CustomFieldDefinition.entity_type == entity_type)
    return session.exec(query).all()


@app.post("/custom-field-values", response_model=CustomFieldValue)
def set_custom_field_value(value: CustomFieldValueCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if current_user.role not in {"master", "company_admin", "employee"}:
        raise HTTPException(status_code=403, detail="Keine Berechtigung")
    db_value = CustomFieldValue(**value.dict())
    session.add(db_value)
    session.commit()
    session.refresh(db_value)
    return db_value


@app.get("/custom-field-values/{entity_type}/{entity_id}", response_model=List[CustomFieldValue])
def get_custom_values(entity_type: str, entity_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if current_user.role not in {"master", "company_admin", "employee"}:
        raise HTTPException(status_code=403, detail="Keine Berechtigung")
    statement = select(CustomFieldValue).where(
        CustomFieldValue.entity_type == entity_type, CustomFieldValue.entity_id == entity_id
    )
    return session.exec(statement).all()


@app.get("/health")
def healthcheck():
    return {"status": "ok", "timestamp": datetime.utcnow()}

