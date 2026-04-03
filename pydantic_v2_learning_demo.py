#!/usr/bin/env python3
"""
Pydantic v2 Learning Demo
-------------------------
A single, beginner-friendly script that demonstrates core + advanced Pydantic v2 features.

Run:
    python pydantic_v2_learning_demo.py
"""

from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Dict, List, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


# ============================================================================
# 1) BASICS: BaseModel, type validation, defaults, optional fields
# ============================================================================
class BasicProduct(BaseModel):
    """Simple model to demonstrate core types and defaults."""

    id: int
    name: str
    price: float
    in_stock: bool = True
    description: Optional[str] = None


# ============================================================================
# 2) FIELD CUSTOMIZATION: constraints + descriptions + metadata
# ============================================================================
class ConstrainedUser(BaseModel):
    """Field(...) enables validation constraints and rich metadata."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=20,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Unique username with letters, digits, and underscore only.",
        examples=["alice_01"],
    )
    age: int = Field(..., gt=0, lt=130, description="Age must be between 1 and 129.")
    rating: float = Field(0.0, ge=0.0, le=5.0, description="User rating from 0.0 to 5.0.")


# ============================================================================
# 3) NESTED MODELS: model inside model
# ============================================================================
class Address(BaseModel):
    street: str
    city: str
    postal_code: str = Field(..., pattern=r"^\d{5}$", description="5-digit ZIP code")


class UserProfile(BaseModel):
    user_id: int
    full_name: str
    address: Address


# ============================================================================
# 4) LISTS + COMPLEX TYPES: List, Dict, Optional, Union
# ============================================================================
class InventoryItem(BaseModel):
    sku: str = Field(..., min_length=5)
    tags: List[str] = Field(default_factory=list)
    attributes: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)
    discount: Optional[float] = Field(None, ge=0.0, le=100.0)


class Inventory(BaseModel):
    items: List[InventoryItem]

    @field_validator("items")
    @classmethod
    def ensure_not_empty(cls, value: List[InventoryItem]) -> List[InventoryItem]:
        if not value:
            raise ValueError("Inventory must contain at least one item.")
        return value


# ============================================================================
# 5) VALIDATORS: field + model validators (before and after)
# ============================================================================
class RegistrationForm(BaseModel):
    email: str
    password: str
    confirm_password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        # PRE validation: cleanup before core parsing/validation
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        # POST field validation: ensure stronger password policy
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if value.isalpha() or value.isdigit():
            raise ValueError("Password must contain a mix of letters and numbers.")
        return value

    @model_validator(mode="after")
    def passwords_match(self) -> "RegistrationForm":
        # POST model validation: check cross-field logic
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password do not match.")
        return self


# ============================================================================
# 6, 7, 8, 9, 11) ADVANCED + SERIALIZATION + PARSING + ERRORS + REAL-WORLD API
# ============================================================================
class Price(Decimal):
    """Custom type aliasing Decimal for readability in financial models."""


class APIRequest(BaseModel):
    """Real-world style request schema (e.g., place an order)."""

    model_config = ConfigDict(populate_by_name=True)

    request_id: str = Field(..., min_length=8)
    user_id: int = Field(..., alias="userId", gt=0)
    product_ids: List[int] = Field(..., min_length=1)
    shipping: Address
    coupon_code: Optional[str] = Field(None, pattern=r"^[A-Z0-9]{4,10}$")

    @field_validator("product_ids", mode="before")
    @classmethod
    def coerce_product_ids(cls, value):
        # PRE validator: accept comma-separated string and turn it into a list
        if isinstance(value, str):
            return [int(x.strip()) for x in value.split(",") if x.strip()]
        return value


class APIResponse(BaseModel):
    """Real-world style response schema with computed field and immutability."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    status: str = Field(..., pattern=r"^(created|failed|shipped)$")
    subtotal: Price = Field(..., gt=Decimal("0"))
    tax_rate: float = Field(0.08, ge=0, le=1)

    @computed_field
    @property
    def total(self) -> Decimal:
        return self.subtotal * Decimal(str(1 + self.tax_rate))


# ============================================================================
# 10) SETTINGS MANAGEMENT: BaseSettings + environment variables
# ============================================================================
class AppSettings(BaseSettings):
    """Loads configuration from environment variables."""

    model_config = SettingsConfigDict(env_prefix="APP_", case_sensitive=False)

    app_name: str = "PydanticDemo"
    debug: bool = False
    max_connections: int = 10


# ============================================================================
# Utility helpers for clean console output
# ============================================================================
def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_validation_error(exc: ValidationError) -> None:
    print("ValidationError occurred!")
    print("Human-readable message:")
    print(str(exc))
    print("\nStructured errors (exc.errors()):")
    print(json.dumps(exc.errors(), indent=2))


# ============================================================================
# Main demo flow
# ============================================================================
def main() -> None:
    # 1) Basics
    print_section("1) Basics: BaseModel + Type Validation + Defaults + Optional")
    product = BasicProduct(id=1, name="Keyboard", price=49.99)
    print("Valid BasicProduct:", product)
    print("As dict:", product.model_dump())

    # Demonstrate automatic coercion/validation (string -> int/float/bool)
    product_from_strings = BasicProduct(
        id="2", name="Mouse", price="19.95", in_stock="true", description=None
    )
    print("Coerced from strings:", product_from_strings)

    # 2) Field customization
    print_section("2) Field Customization: constraints + descriptions + metadata")
    user = ConstrainedUser(username="alice_01", age=30, rating=4.7)
    print("Valid ConstrainedUser:", user.model_dump())
    print("JSON schema snippet has descriptions/examples available:")
    print(json.dumps(ConstrainedUser.model_json_schema()["properties"], indent=2))

    # 3) Nested models
    print_section("3) Nested Models")
    profile = UserProfile(
        user_id=101,
        full_name="Alice Johnson",
        address=Address(street="12 Main St", city="Boston", postal_code="02108"),
    )
    print("Nested profile:", profile.model_dump())

    # 4) Lists and complex types
    print_section("4) Lists + Dict + Optional + Union")
    inventory = Inventory(
        items=[
            InventoryItem(
                sku="SKU-100",
                tags=["electronics", "sale"],
                attributes={"color": "black", "weight": 1.2, "featured": True},
                discount=10,
            )
        ]
    )
    print("Validated inventory:", inventory.model_dump())

    # 5) Validators (field + model, pre + post)
    print_section("5) Validators: field_validator + model_validator")
    form = RegistrationForm(
        email="  STUDENT@EXAMPLE.COM ",
        password="abc12345",
        confirm_password="abc12345",
    )
    print("Registration form after normalization:", form.model_dump())

    # 6) Serialization
    print_section("6) Serialization: model_dump + model_dump_json")
    print("APIRequest as dict:")
    request = APIRequest(
        request_id="REQ00001",
        userId=7,  # alias field usage
        product_ids=[101, 102],
        shipping={"street": "77 Park Ave", "city": "NYC", "postal_code": "10001"},
    )
    print(request.model_dump())
    print("APIRequest as JSON:")
    print(request.model_dump_json(indent=2))

    # 7) Parsing
    print_section("7) Parsing: model_validate + model_validate_json")
    raw_data = {
        "request_id": "REQ00002",
        "userId": 8,
        "product_ids": "201, 202, 203",  # intentionally string to trigger PRE validator
        "shipping": {"street": "45 Ocean Dr", "city": "Miami", "postal_code": "33139"},
    }
    parsed_request = APIRequest.model_validate(raw_data)
    print("Parsed from dict using model_validate:", parsed_request.model_dump())

    raw_json = json.dumps(raw_data)
    parsed_from_json = APIRequest.model_validate_json(raw_json)
    print("Parsed from JSON string using model_validate_json:", parsed_from_json.model_dump())

    # 8) Error handling
    print_section("8) Error Handling: clear and structured output")
    try:
        _bad_user = ConstrainedUser(username="x!", age=-1, rating=9.9)
    except ValidationError as exc:
        print_validation_error(exc)

    try:
        _bad_form = RegistrationForm(
            email="bad@example.com",
            password="123",
            confirm_password="different",
        )
    except ValidationError as exc:
        print_validation_error(exc)

    # 9) Advanced features: computed field + alias + immutable + custom type
    print_section("9) Advanced: computed_field + alias + immutable + custom type")
    response = APIResponse(order_id="ORD-900", status="created", subtotal=Decimal("120.50"))
    print("Response dict (includes computed total):", response.model_dump())
    print("Response JSON:", response.model_dump_json(indent=2))

    print("Attempting to mutate immutable APIResponse...")
    try:
        response.status = "shipped"  # type: ignore[misc]
    except ValidationError as exc:
        print("Immutable model blocked mutation as expected:")
        print(exc)
    except Exception as exc:
        print("Mutation raised exception as expected:", repr(exc))

    # 10) Settings management
    print_section("10) BaseSettings: environment variable loading")
    os.environ["APP_APP_NAME"] = "LearningPlatform"
    os.environ["APP_DEBUG"] = "true"
    os.environ["APP_MAX_CONNECTIONS"] = "25"
    settings = AppSettings()
    print("Loaded settings from env:", settings.model_dump())

    # 11) Real-world scenario summary
    print_section("11) Real-world flow: request -> response")
    print("Incoming API request:", request.model_dump(by_alias=True))
    print("Outgoing API response:", response.model_dump())

    # 12) End note
    print_section("12) Complete")
    print("This script covered Pydantic v2 basics through advanced patterns.")


if __name__ == "__main__":
    main()
