"""PTX's mapping of the property tables. Ward and Locality are read-only references owned by core_service."""
import datetime
import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from urban_common.db import Base


class Ward(Base):
    __tablename__ = "wards"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(50), nullable=False)
    ward_number = Column(Integer, nullable=False)
    ward_name = Column(String(100), nullable=False)


class Locality(Base):
    __tablename__ = "localities"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(50), nullable=False)
    locality_name = Column(String(150), nullable=False)


class PropertyParcel(Base):
    __tablename__ = "property_parcels"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), nullable=False, index=True)
    ulpin = Column(String(50), unique=True, nullable=False, index=True)
    survey_number = Column(String(50), nullable=False)
    plot_number = Column(String(50), nullable=True)
    total_area_sqyd = Column(Float, nullable=False)
    ward_id = Column(String(36), ForeignKey("wards.id"), nullable=False, index=True)
    locality_id = Column(String(36), ForeignKey("localities.id"), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    ward = relationship("Ward")
    locality = relationship("Locality")
    buildings = relationship("Building", back_populates="parcel", cascade="all, delete-orphan")


class Building(Base):
    __tablename__ = "buildings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), nullable=False, index=True)
    parcel_id = Column(String(36), ForeignKey("property_parcels.id"), nullable=False, index=True)
    building_name = Column(String(150), nullable=True)
    building_type = Column(String(50), nullable=False)
    total_floors = Column(Integer, default=1)
    construction_year = Column(Integer, nullable=True)
    building_permission_no = Column(String(100), nullable=True)

    parcel = relationship("PropertyParcel", back_populates="buildings")
    units = relationship("PropertyUnit", back_populates="building", cascade="all, delete-orphan")


class PropertyUnit(Base):
    __tablename__ = "property_units"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), nullable=False, index=True)
    building_id = Column(String(36), ForeignKey("buildings.id"), nullable=False, index=True)
    ptin = Column(String(30), unique=True, nullable=False, index=True)
    unit_number = Column(String(50), nullable=False)
    floor_number = Column(Integer, default=0)
    usage_category = Column(String(50), nullable=False)
    carpet_area_sqft = Column(Float, nullable=False)
    built_up_area_sqft = Column(Float, nullable=False)
    occupancy_type = Column(String(30), nullable=False)
    annual_rental_value = Column(Numeric(12, 2), default=0.0)
    current_demand_amount = Column(Numeric(12, 2), default=0.0)
    tax_status = Column(String(30), default="PAID")

    building = relationship("Building", back_populates="units")
    owners = relationship("Owner", back_populates="unit", cascade="all, delete-orphan")


class Owner(Base):
    __tablename__ = "owners"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), nullable=False, index=True)
    unit_id = Column(String(36), ForeignKey("property_units.id"), nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    mobile_number = Column(String(15), nullable=False, index=True)
    email = Column(String(100), nullable=True)
    aadhaar_vault_ref = Column(String(64), nullable=True)
    ownership_share = Column(Float, default=100.0)

    unit = relationship("PropertyUnit", back_populates="owners")
