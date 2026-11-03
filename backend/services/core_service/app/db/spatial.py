"""PostGIS columns and the triggers that keep them correct, whichever service writes the row. Idempotent."""

SPATIAL_STATEMENTS = [
    # Backfilling touches rows under row-level security, so this transaction needs to see them all.
    "SELECT set_config('app.rls_bypass', 'on', true)",
    "ALTER TABLE property_parcels ADD COLUMN IF NOT EXISTS geom geometry(Geometry, 4326)",
    "ALTER TABLE property_parcels ADD COLUMN IF NOT EXISTS boundary_geom geometry(Geometry, 4326)",
    "ALTER TABLE property_parcels ADD COLUMN IF NOT EXISTS survey_status varchar(30)",
    "ALTER TABLE wards ADD COLUMN IF NOT EXISTS geom geometry(Geometry, 4326)",
    "ALTER TABLE zones ADD COLUMN IF NOT EXISTS geom geometry(Geometry, 4326)",
    "CREATE INDEX IF NOT EXISTS ix_property_parcels_geom ON property_parcels USING gist (geom)",
    "CREATE INDEX IF NOT EXISTS ix_wards_geom ON wards USING gist (geom)",
    "CREATE INDEX IF NOT EXISTS ix_zones_geom ON zones USING gist (geom)",
    """
    CREATE OR REPLACE FUNCTION gis_sync_parcel_geom() RETURNS trigger AS $$
    BEGIN
        IF NEW.latitude IS NULL OR NEW.longitude IS NULL
           OR NEW.latitude NOT BETWEEN -90 AND 90 OR NEW.longitude NOT BETWEEN -180 AND 180 THEN
            NEW.geom := NULL;
        ELSE
            NEW.geom := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,
    """
    CREATE OR REPLACE FUNCTION gis_sync_ward_geom() RETURNS trigger AS $$
    BEGIN
        NEW.geom := ST_SetSRID(ST_Multi(ST_GeomFromGeoJSON(NEW.boundary_geometry::text)), 4326);
        IF NOT ST_IsValid(NEW.geom) THEN
            NEW.geom := NULL;
        END IF;
        RETURN NEW;
    EXCEPTION WHEN OTHERS THEN
        -- A malformed boundary leaves the ward unmapped rather than blocking the ward's own save.
        NEW.geom := NULL;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,
    """
    CREATE OR REPLACE TRIGGER trg_gis_parcel_geom BEFORE INSERT OR UPDATE OF latitude, longitude ON property_parcels
    FOR EACH ROW EXECUTE FUNCTION gis_sync_parcel_geom()
    """,
    """
    CREATE OR REPLACE TRIGGER trg_gis_ward_geom BEFORE INSERT OR UPDATE OF boundary_geometry ON wards
    FOR EACH ROW EXECUTE FUNCTION gis_sync_ward_geom()
    """,
    "UPDATE property_parcels SET latitude = latitude WHERE geom IS NULL AND latitude IS NOT NULL",
    "UPDATE wards SET boundary_geometry = boundary_geometry WHERE geom IS NULL AND boundary_geometry IS NOT NULL",
]
