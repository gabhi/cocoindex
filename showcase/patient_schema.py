"""Pydantic schema for the Patient Intake extraction demo.

Mirrors examples/patient_intake_extraction_dspy/models.py so the live demo
produces the same structured shape as the real example. Copied rather than
imported since that example is its own standalone project (own pyproject.toml,
not installable as a package from here).
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, Field


class Contact(BaseModel):
    name: str
    phone: str
    relationship: str


class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str


class Pharmacy(BaseModel):
    name: str
    phone: str
    address: Address


class Insurance(BaseModel):
    provider: str
    policy_number: str
    group_number: str | None = None
    policyholder_name: str
    relationship_to_patient: str


class Condition(BaseModel):
    name: str
    diagnosed: bool


class Medication(BaseModel):
    name: str
    dosage: str


class Allergy(BaseModel):
    name: str


class Surgery(BaseModel):
    name: str
    date: str


class Patient(BaseModel):
    """Complete patient information extracted from an intake form."""

    name: str
    dob: datetime.date
    gender: str
    address: Address
    phone: str
    email: str
    preferred_contact_method: str
    emergency_contact: Contact
    insurance: Insurance | None = None
    reason_for_visit: str
    symptoms_duration: str
    past_conditions: list[Condition] = Field(default_factory=list)
    current_medications: list[Medication] = Field(default_factory=list)
    allergies: list[Allergy] = Field(default_factory=list)
    surgeries: list[Surgery] = Field(default_factory=list)
    occupation: str | None = None
    pharmacy: Pharmacy | None = None
    consent_given: bool
    consent_date: str | None = None
