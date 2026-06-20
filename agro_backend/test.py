import os, uuid
from sqlalchemy import create_engine, text
sync_url = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://agro:" + os.environ["POSTGRES_PASSWORD"] + "@localhost:5433/agro",
)
e = create_engine(sync_url)
farmer_id = uuid.uuid4()
farm_id = uuid.uuid4()
device_id = "AGR-SMOKE-001"
plot_id = "PLOT_SMOKE_001"
pilot_tenant = "11111111-1111-1111-1111-111111111111"


with e.begin() as c:
    c.execute(text("""
        INSERT INTO farmers (farmer_id, tenant_id, full_name, marathi_name, phone_primary,
            whatsapp_number, language_preference, village, taluka, district, state,
            subscription_tier, subscription_start, subscription_end, payment_status)
        VALUES (:f, :t, 'Smoke', 'अ', '+910000000000', '+910000000000', 'marathi',
                'v', 't', 'd', 'Maharashtra', 'basic',
                '2025-06-01', '2026-06-01', 'paid')
    """), {"f": farmer_id, "t": pilot_tenant})
    c.execute(text("""
        INSERT INTO farms (farm_id, tenant_id, farmer_id, total_area_acre,
            gps_lat_center, gps_lng_center, soil_type, water_source_primary,
            irrigation_type, electricity_source)
        VALUES (:fm, :t, :f, 1.0, 19.9, 75.7, 'black', 'well', 'drip', 'grid')
    """), {"fm": farm_id, "t": pilot_tenant, "f": farmer_id})
    c.execute(text("""
    INSERT INTO device_registry (
        device_id, tenant_id, device_type, serial_number,
        mac_address, qr_code_data, farm_id, device_tier,
        installation_date, device_status
    ) VALUES (
        :d, :t, 'sub_node', 'SMOKE001',
        '02:00:00:00:00:01', 'QR_SMOKE001', :fm, 'basic',
        '2025-06-01', 'online'
    )
    """), {"d": device_id, "t": pilot_tenant, "fm": farm_id})
    c.execute(text("""
        INSERT INTO plots (plot_id, tenant_id, farm_id, plot_number, area_acre,
            gps_lat, gps_lng, irrigation_valve_id, node_id)
        VALUES (:p, :t, :fm, 1, 1.0, 19.9, 75.7, 'V1', :d)
    """), {"p": plot_id, "t": pilot_tenant, "fm": farm_id, "d": device_id})


print("Seeded:")
print("  tenant_id =", pilot_tenant)
print("  farmer_id =", farmer_id)
print("  farm_id   =", farm_id)
print("  plot_id   =", plot_id)
print("  node_id   =", device_id)