import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Tenant, Zone, Ward, Locality, PropertyParcel, Building, PropertyUnit, Owner, User
from app.core.security import hash_password
from app.db.session import engine, Base

logger = logging.getLogger(__name__)

async def seed_initial_data(db: AsyncSession):
    # Check and seed GWMC tenant
    existing_gwmc = await db.scalar(select(Tenant).where(Tenant.tenant_id == "GWMC"))
    if not existing_gwmc:
        logger.info("Seeding initial GWMC municipal data...")

        # Tenant
        tenant = Tenant(
            tenant_id="GWMC",
            name="Greater Warangal Municipal Corporation",
            state_code="TG",
            district="Hanamkonda & Warangal"
        )
        db.add(tenant)
    await db.flush()

    # Zones
    z1 = Zone(tenant_id="GWMC", code="ZONE-1", name="Kazipet Zone")
    z2 = Zone(tenant_id="GWMC", code="ZONE-2", name="Hanamkonda Zone")
    z3 = Zone(tenant_id="GWMC", code="ZONE-3", name="Warangal Zone")
    db.add_all([z1, z2, z3])
    await db.flush()

    # Wards
    w1 = Ward(tenant_id="GWMC", zone_id=z2.id, ward_number=14, ward_name="Subedari", councilor_name="Smt. K. Saritha")
    w2 = Ward(tenant_id="GWMC", zone_id=z2.id, ward_number=22, ward_name="Balasamudram", councilor_name="Sri P. Rajesh")
    w3 = Ward(tenant_id="GWMC", zone_id=z2.id, ward_number=35, ward_name="Nakkalagutta", councilor_name="Sri V. Mohan Rao")
    w4 = Ward(tenant_id="GWMC", zone_id=z1.id, ward_number=48, ward_name="KU Campus Road", councilor_name="Dr. T. Radhika")
    w5 = Ward(tenant_id="GWMC", zone_id=z3.id, ward_number=56, ward_name="Mandi Bazar", councilor_name="Sri M. Srinivas")
    db.add_all([w1, w2, w3, w4, w5])
    await db.flush()

    # Localities
    loc1 = Locality(tenant_id="GWMC", ward_id=w1.id, locality_code="LOC-14-01", locality_name="Postal Colony", pincode="506001")
    loc2 = Locality(tenant_id="GWMC", ward_id=w2.id, locality_code="LOC-22-01", locality_name="Judicial Complex Enclave", pincode="506001")
    loc3 = Locality(tenant_id="GWMC", ward_id=w3.id, locality_code="LOC-35-01", locality_name="Green Meadows Avenue", pincode="506002")
    db.add_all([loc1, loc2, loc3])
    await db.flush()

    # Sample Properties
    sample_props = [
        {
            "ulpin": "TG-GWMC-506001-00123",
            "survey": "142/A",
            "plot": "Plot 12",
            "area": 250.0,
            "ward": w1,
            "loc": loc1,
            "lat": 17.9812,
            "lng": 79.5982,
            "addr": "H.No 2-4-123, Postal Colony, Subedari, Hanamkonda",
            "bldg_name": "Sri Lakshmi Nivas",
            "bldg_type": "Residential",
            "floors": 2,
            "perm": "GWMC/BP/2022/1049",
            "ptin": "1081400234",
            "unit": "G-1",
            "usage": "Residential",
            "carpet": 1150.0,
            "builtup": 1380.0,
            "demand": 4250.0,
            "status": "PAID",
            "owner": "K. Venkateshwarlu",
            "mobile": "9848022331",
            "email": "kvenkat@example.com"
        },
        {
            "ulpin": "TG-GWMC-506001-00456",
            "survey": "198/B",
            "plot": "Plot 45",
            "area": 480.0,
            "ward": w2,
            "loc": loc2,
            "lat": 17.9891,
            "lng": 79.6015,
            "addr": "H.No 3-8-45, Judicial Complex Enclave, Balasamudram",
            "bldg_name": "Balaji Heights Commercial Complex",
            "bldg_type": "Commercial",
            "floors": 4,
            "perm": "GWMC/BP/2021/8874",
            "ptin": "1082200561",
            "unit": "F-101",
            "usage": "Commercial",
            "carpet": 2400.0,
            "builtup": 2950.0,
            "demand": 28400.0,
            "status": "DUE",
            "owner": "Ch. Narayana Rao",
            "mobile": "9440155220",
            "email": "narayana.ch@example.com"
        },
        {
            "ulpin": "TG-GWMC-506002-00789",
            "survey": "88/C",
            "plot": "Plot 88",
            "area": 300.0,
            "ward": w3,
            "loc": loc3,
            "lat": 17.9945,
            "lng": 79.5872,
            "addr": "H.No 1-12-88, Green Meadows Avenue, Nakkalagutta",
            "bldg_name": "Ananya Residency",
            "bldg_type": "Residential",
            "floors": 3,
            "perm": "GWMC/BP/2023/4521",
            "ptin": "1083500912",
            "unit": "Flat-202",
            "usage": "Residential",
            "carpet": 1320.0,
            "builtup": 1600.0,
            "demand": 6800.0,
            "status": "PAID",
            "owner": "P. Sudhakar Reddy",
            "mobile": "9989044112",
            "email": "sudhakar.p@example.com"
        },
        {
            "ulpin": "TG-GWMC-506004-00101",
            "survey": "310/2",
            "plot": "Plot 101",
            "area": 600.0,
            "ward": w4,
            "loc": None,
            "lat": 18.0125,
            "lng": 79.5714,
            "addr": "H.No 5-2-101, Main Road, KU Campus Road, Kazipet",
            "bldg_name": "Kakatiya Tech Park Building A",
            "bldg_type": "Commercial",
            "floors": 5,
            "perm": "GWMC/BP/2020/3310",
            "ptin": "1084800115",
            "unit": "Unit-3A",
            "usage": "Commercial",
            "carpet": 4500.0,
            "builtup": 5400.0,
            "demand": 54600.0,
            "status": "ARREARS",
            "owner": "Kakatiya Infotech Pvt Ltd",
            "mobile": "9701233445",
            "email": "admin@kakatiyainfotech.com"
        },
        {
            "ulpin": "TG-GWMC-506001-00202",
            "survey": "55/1",
            "plot": "Plot 20",
            "area": 180.0,
            "ward": w1,
            "loc": loc1,
            "lat": 17.9825,
            "lng": 79.5991,
            "addr": "H.No 2-4-202, Postal Colony Extension, Subedari",
            "bldg_name": "Sai Ram Nilayam",
            "bldg_type": "Residential",
            "floors": 1,
            "perm": "GWMC/BP/2019/1204",
            "ptin": "1081400889",
            "unit": "Ground-Floor",
            "usage": "Residential",
            "carpet": 850.0,
            "builtup": 1020.0,
            "demand": 2950.0,
            "status": "PAID",
            "owner": "G. Manjula",
            "mobile": "9866123456",
            "email": "manjula.g@example.com"
        }
    ]

    for sp in sample_props:
        p = PropertyParcel(
            tenant_id="GWMC",
            ulpin=sp["ulpin"],
            survey_number=sp["survey"],
            plot_number=sp["plot"],
            total_area_sqyd=sp["area"],
            ward_id=sp["ward"].id,
            locality_id=sp["loc"].id if sp["loc"] else None,
            latitude=sp["lat"],
            longitude=sp["lng"],
            address=sp["addr"]
        )
        db.add(p)
        await db.flush()

        b = Building(
            tenant_id="GWMC",
            parcel_id=p.id,
            building_name=sp["bldg_name"],
            building_type=sp["bldg_type"],
            total_floors=sp["floors"],
            building_permission_no=sp["perm"]
        )
        db.add(b)
        await db.flush()

        u = PropertyUnit(
            tenant_id="GWMC",
            building_id=b.id,
            ptin=sp["ptin"],
            unit_number=sp["unit"],
            usage_category=sp["usage"],
            carpet_area_sqft=sp["carpet"],
            built_up_area_sqft=sp["builtup"],
            occupancy_type="Owner",
            current_demand_amount=sp["demand"],
            tax_status=sp["status"]
        )
        db.add(u)
        await db.flush()

        o = Owner(
            tenant_id="GWMC",
            unit_id=u.id,
            full_name=sp["owner"],
            mobile_number=sp["mobile"],
            email=sp["email"]
        )
        db.add(o)

    # Seed Demo SSO Users with Module Access
    all_19 = "PTX,WTR,GRV,FIN,DMS,TRL,UCH,BPM,TPL,FNC,SWM,ENG,SLM,PRK,INV,HRM,MPM,LGL,GSC"
    demo_users = [
        User(
            tenant_id="GWMC",
            username="admin@urban.gov.in",
            email="admin@urban.gov.in",
            password_hash=hash_password("Admin@123"),
            full_name="Suresh Kumar (State Admin)",
            role="super_admin",
            assigned_modules=all_19
        ),
        User(
            tenant_id="GWMC",
            username="officer@gwmc.gov.in",
            email="officer@gwmc.gov.in",
            password_hash=hash_password("Officer@123"),
            full_name="Ramesh Reddy (Revenue Officer)",
            role="revenue_officer",
            assigned_modules="PTX,WTR,TRL,UCH,MPM,FIN,DMS",
            assigned_zone="Zone-1",
            assigned_ward="Ward-14"
        ),
        User(
            tenant_id="GWMC",
            username="planner@gwmc.gov.in",
            email="planner@gwmc.gov.in",
            password_hash=hash_password("Planner@123"),
            full_name="Ananya Sharma (Town Planning Officer)",
            role="town_planner",
            assigned_modules="BPM,TPL,FNC,DMS,LGL",
            assigned_zone="Zone-2"
        ),
        User(
            tenant_id="GWMC",
            username="citizen@gmail.com",
            email="citizen@gmail.com",
            password_hash=hash_password("Citizen@123"),
            full_name="K. Venkateshwarlu (Citizen)",
            role="citizen",
            assigned_modules="GRV,PTX,WTR,TRL,GSC,DMS",
            assigned_ward="Ward-14"
        )
    ]
    db.add_all(demo_users)

    await db.commit()
    logger.info("GWMC initial data & SSO users seeded successfully!")

    # Check and seed second SaaS Tenant: GHMC (Greater Hyderabad Municipal Corporation)
    existing_ghmc = await db.scalar(select(Tenant).where(Tenant.tenant_id == "GHMC"))
    if not existing_ghmc:
        logger.info("Seeding initial GHMC SaaS tenant data...")
        ghmc_tenant = Tenant(
            tenant_id="GHMC",
            name="Greater Hyderabad Municipal Corporation",
            state_code="TG",
            district="Hyderabad"
        )
        db.add(ghmc_tenant)
        await db.flush()

        gz1 = Zone(tenant_id="GHMC", code="ZONE-KH", name="Khairatabad Zone")
        gz2 = Zone(tenant_id="GHMC", code="ZONE-CH", name="Charminar Zone")
        gz3 = Zone(tenant_id="GHMC", code="ZONE-SC", name="Secunderabad Zone")
        db.add_all([gz1, gz2, gz3])
        await db.flush()

        gw1 = Ward(tenant_id="GHMC", zone_id=gz1.id, ward_number=89, ward_name="Banjara Hills", councilor_name="Sri K. Ramakrishna")
        gw2 = Ward(tenant_id="GHMC", zone_id=gz1.id, ward_number=95, ward_name="Jubilee Hills", councilor_name="Smt. M. Madhavi")
        gw3 = Ward(tenant_id="GHMC", zone_id=gz2.id, ward_number=45, ward_name="Charminar Old City", councilor_name="Md. Farooq Ahmed")
        db.add_all([gw1, gw2, gw3])
        await db.flush()

        gloc1 = Locality(tenant_id="GHMC", ward_id=gw1.id, locality_code="LOC-89-01", locality_name="Road No 12 Commercial Belt", pincode="500034")
        gloc2 = Locality(tenant_id="GHMC", ward_id=gw2.id, locality_code="LOC-95-01", locality_name="Jubilee Enclave Heights", pincode="500033")
        db.add_all([gloc1, gloc2])
        await db.flush()

        ghmc_parcel1 = PropertyParcel(
            tenant_id="GHMC",
            ulpin="TG-GHMC-500034-00891",
            survey_number="210/B",
            plot_number="Plot 89A",
            total_area_sqyd=600.0,
            ward_id=gw1.id,
            locality_id=gloc1.id,
            latitude=17.4156,
            longitude=78.4352,
            address="Plot 89A, Road No 12, Banjara Hills, Hyderabad"
        )
        ghmc_parcel2 = PropertyParcel(
            tenant_id="GHMC",
            ulpin="TG-GHMC-500033-00952",
            survey_number="104/1",
            plot_number="Plot 14",
            total_area_sqyd=450.0,
            ward_id=gw2.id,
            locality_id=gloc2.id,
            latitude=17.4325,
            longitude=78.4071,
            address="Plot 14, Road No 36, Jubilee Hills, Hyderabad"
        )
        db.add_all([ghmc_parcel1, ghmc_parcel2])
        await db.flush()

        gb1 = Building(
            tenant_id="GHMC",
            parcel_id=ghmc_parcel1.id,
            building_name="Banjara Corporate Plaza",
            building_type="Commercial",
            total_floors=5,
            construction_year=2021,
            building_permission_no="GHMC/BP/2021/8912"
        )
        gb2 = Building(
            tenant_id="GHMC",
            parcel_id=ghmc_parcel2.id,
            building_name="Jubilee Heights Villa",
            building_type="Residential",
            total_floors=2,
            construction_year=2023,
            building_permission_no="GHMC/BP/2023/4521"
        )
        db.add_all([gb1, gb2])
        await db.flush()

        gu1 = PropertyUnit(
            tenant_id="GHMC",
            building_id=gb1.id,
            ptin="1009871101",
            unit_number="Suite 101",
            floor_number=1,
            usage_category="Commercial",
            carpet_area_sqft=2800.0,
            built_up_area_sqft=3200.0,
            occupancy_type="Tenant",
            annual_rental_value=720000.0,
            current_demand_amount=72000.0,
            tax_status="PAID"
        )
        gu2 = PropertyUnit(
            tenant_id="GHMC",
            building_id=gb2.id,
            ptin="1009872202",
            unit_number="Villa 1",
            floor_number=0,
            usage_category="Residential",
            carpet_area_sqft=3200.0,
            built_up_area_sqft=3800.0,
            occupancy_type="Owner",
            annual_rental_value=96000.0,
            current_demand_amount=9600.0,
            tax_status="DUE"
        )
        db.add_all([gu1, gu2])
        await db.flush()

        go1 = Owner(
            tenant_id="GHMC",
            unit_id=gu1.id,
            full_name="Apollo Infotech Ltd",
            mobile_number="9849011223",
            email="admin@apolloinfo.com",
            ownership_share=100.0
        )
        go2 = Owner(
            tenant_id="GHMC",
            unit_id=gu2.id,
            full_name="K. Taraka Rao",
            mobile_number="9849099887",
            email="taraka.rao@gmail.com",
            ownership_share=100.0
        )
        db.add_all([go1, go2])

        ghmc_officer = User(
            tenant_id="GHMC",
            username="officer@ghmc.gov.in",
            email="officer@ghmc.gov.in",
            password_hash=hash_password("Officer@123"),
            full_name="S. Narsing Rao (GHMC Revenue Officer)",
            role="revenue_officer",
            assigned_modules="PTX,WTR,TRL,UCH,MPM,FIN,DMS",
            assigned_zone="Khairatabad Zone",
            assigned_ward="Ward-89"
        )
        db.add(ghmc_officer)
        await db.commit()
        logger.info("GHMC SaaS tenant & demo data seeded successfully!")

