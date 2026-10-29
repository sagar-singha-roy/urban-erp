import datetime
import uuid
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, Numeric
)
from sqlalchemy.orm import relationship
from app.db.session import Base

class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    state_code = Column(String(10), nullable=False, default="TG")
    district = Column(String(100), nullable=False, default="Warangal")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    zones = relationship("Zone", back_populates="tenant", cascade="all, delete-orphan")
    parcels = relationship("PropertyParcel", back_populates="tenant", cascade="all, delete-orphan")

class Zone(Base):
    __tablename__ = "zones"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)

    tenant = relationship("Tenant", back_populates="zones")
    wards = relationship("Ward", back_populates="zone", cascade="all, delete-orphan")

class Ward(Base):
    __tablename__ = "wards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    zone_id = Column(String(36), ForeignKey("zones.id"), nullable=False, index=True)
    ward_number = Column(Integer, nullable=False, index=True)
    ward_name = Column(String(100), nullable=False)
    councilor_name = Column(String(100), nullable=True)

    zone = relationship("Zone", back_populates="wards")
    localities = relationship("Locality", back_populates="ward", cascade="all, delete-orphan")
    parcels = relationship("PropertyParcel", back_populates="ward")

class Locality(Base):
    __tablename__ = "localities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    ward_id = Column(String(36), ForeignKey("wards.id"), nullable=False, index=True)
    locality_code = Column(String(30), nullable=False)
    locality_name = Column(String(150), nullable=False)
    pincode = Column(String(10), nullable=False)

    ward = relationship("Ward", back_populates="localities")
    parcels = relationship("PropertyParcel", back_populates="locality")

class PropertyParcel(Base):
    __tablename__ = "property_parcels"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
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

    tenant = relationship("Tenant", back_populates="parcels")
    ward = relationship("Ward", back_populates="parcels")
    locality = relationship("Locality", back_populates="parcels")
    buildings = relationship("Building", back_populates="parcel", cascade="all, delete-orphan")

class Building(Base):
    __tablename__ = "buildings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), nullable=False, index=True)
    parcel_id = Column(String(36), ForeignKey("property_parcels.id"), nullable=False, index=True)
    
    building_name = Column(String(150), nullable=True)
    building_type = Column(String(50), nullable=False) # Residential, Commercial, Mixed, Industrial
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
    
    ptin = Column(String(30), unique=True, nullable=False, index=True) # 10-digit Property Tax Identification Number
    unit_number = Column(String(50), nullable=False)
    floor_number = Column(Integer, default=0) # 0 = Ground
    usage_category = Column(String(50), nullable=False) # Residential, Commercial, Institutional, Vacant Land
    
    carpet_area_sqft = Column(Float, nullable=False)
    built_up_area_sqft = Column(Float, nullable=False)
    occupancy_type = Column(String(30), nullable=False) # Owner, Tenant, Vacant
    
    annual_rental_value = Column(Numeric(12, 2), default=0.0)
    current_demand_amount = Column(Numeric(12, 2), default=0.0)
    tax_status = Column(String(30), default="PAID") # PAID, DUE, ARREARS, EXEMPT

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
    ownership_share = Column(Float, default=100.0) # Percentage

    unit = relationship("PropertyUnit", back_populates="owners")

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id"), nullable=False, default="GWMC")
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), nullable=False, default="citizen") # super_admin, revenue_officer, town_planner, engineering_officer, citizen
    assigned_modules = Column(Text, nullable=False, default="GRV,PTX,WTR") # Comma-separated list of 19 module codes
    assigned_zone = Column(String(50), nullable=True)
    assigned_ward = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

