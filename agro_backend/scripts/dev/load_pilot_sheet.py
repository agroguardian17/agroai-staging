"""Load the pilot intake sheet values into the DB (one-time, idempotent).

Applies the human-entered values (sources FI / FO / TECH / OPS / DEALER) from
"Viraai agri ai Database" onto the seeded pilot records:

  tenant 11111111…, farmer aaaaaaaa…, farm bbbbbbbb…, PLOT_PILOT_001 and its
  active Ginger season, the Main Node AGR-MN-0001, and a technician install row.

Values are normalized to the DB's CHECK domains (lower-cased enums, yes/no →
bool, DD/MM/YYYY → date, electricity multi-select → comma list). Requires the
enum-widening migration 0020. Reads DATABASE_URL_SYNC (same as seed_pilot).
Re-runnable: every write is an UPDATE or an ON CONFLICT upsert.

    docker compose -f docker-compose.prod.yml exec app python -m scripts.dev.load_pilot_sheet
"""

# This file carries intentional Marathi text (names, plot/fertilizer notes) with
# Devanagari digits; RUF001's ambiguous-character warning is a false positive here.
# ruff: noqa: RUF001
from __future__ import annotations

import os
from datetime import date

from sqlalchemy import create_engine, text

PILOT_TENANT = "11111111-1111-1111-1111-111111111111"
FARMER_ID = "aaaaaaaa-1111-1111-1111-111111111111"
FARM_ID = "bbbbbbbb-2222-2222-2222-222222222222"
PLOT_ID = "PLOT_PILOT_001"
MAIN_NODE_ID = "AGR-MN-0001"
INSTALL_ID = "dddddddd-4444-4444-4444-000000000001"  # fixed → idempotent upsert

# --- Normalized values (mapped to the DB CHECK domains) --------------------
TENANTS = {"name": "Viraai", "tier": "pilot_internal"}

FARMERS = {
    "full_name": "Sheshrao Asaram Kale",
    "marathi_name": "शेषराव आसाराम काळे",
    "phone_primary": "9673600074",
    "phone_secondary": "7021198781",
    "whatsapp_number": "9673600074",
    "language_preference": "marathi",
    "village": "Jalgaon Ghat",
    "taluka": "Kannad",
    "district": "Chhatrapati Sambhajinagar",
    "state": "Maharashtra",
    "pin_code": "431103",
    "aadhar_number": "694332716588",
    "farmer_id_govt": "48212868552",
    "education_level": "primary",
    "age_years": 67,
    "gender": "male",
    "account_status": "active",
    "subscription_tier": "basic",
    "referred_by": "Kailas Kale",
}

FARMS = {
    "farm_name": "मळ्याचे वावर",
    "survey_number": "56",
    "total_area_acre": 14,
    "gps_lat_center": 20.14080177,
    "gps_lng_center": 75.08394417,
    "soil_type": "black",
    "soil_organic_carbon_pct": 0.55,
    "terrain_type": "flat",
    "water_source_primary": "well",
    "water_source_secondary": "dam",  # needs migration 0020
    "well_depth_ft": 72,
    "irrigation_type": "drip",
    "drip_emitter_lph": 4,
    "irrigation_area_acre": 6,
    "electricity_source": "grid,solar_pump",  # multi-select; needs migration 0020
    "solar_pump_hp": 3,
    "electricity_feeder_name": "Takali",
    "electricity_schedule_known": True,
    "road_access": True,
    "nearest_town_km": 1,
    "mobile_network_quality": "good",  # needs migration 0020
}

PLOTS = {
    "plot_number": 1,
    "plot_name": "अद्रकीचा प्लॉट",
    "area_acre": 0.75,
    "gps_lat": 20.14092619,
    "gps_lng": 75.08390653,
    "soil_type_override": "black",
    "drip_line_count": 37,
    "plot_status": "active",
}

CROP_SEASON = {
    "season_name": "Kharif 2026 - Ginger",
    "season_type": "kharif",
    "year": 2026,
    "crop_name_marathi": "अद्रक",
    "crop_name_english": "Ginger",
    "crop_variety": "Mahima",
    "crop_category": "vegetable",
    "sowing_date": date(2026, 6, 13),
    "transplanting_date": date(2026, 6, 13),
    "expected_harvest_date": date(2027, 6, 13),
    "seed_rate_kg_per_acre": 700,
    "seed_cost_per_kg": 8000,
    "base_fertilizer_at_sowing": (
        "कुजलेले शेणखत ६ ट्रोली, वर्मीकंपोस्ट १० क्विंटल, निंबोळी पेड १४० किलो, "
        "zinCo गोल्ड 33% १० किलो, G५ Soil Enricher २० किलो, Plantation Special ५ किलो, "
        "AP५० Fertinix ६ किलो, बॉरोक्स 1 किलो, मग्नेशीयम sulphate 15 किलो, Seweed Gr ६ किलो, "
        "Ferrous Sulphate 15 kg, Magnees Sulphate 1 kg, Sulphour 6 kg"
    ),
    "target_yield_qtl_per_acre": 300,
    "season_status": "active",
}

DEVICE_MAIN = {"pole_height_ft": 8, "enclosure_type": "IP65", "sim_provider": "airtel"}

# technician_installations: no existing row → insert one. NOT-NULL columns
# without a sheet value are placeholders (technician_* TBD, visit_date = sowing).
TECH_INSTALL = {
    "installation_id": INSTALL_ID,
    "tenant_id": PILOT_TENANT,
    "technician_id": "TECH-PILOT-01",
    "technician_name": "TBD",
    "technician_phone": "TBD",
    "farm_id": FARM_ID,
    "farmer_id": FARMER_ID,
    "visit_type": "installation",
    "visit_date": date(2026, 6, 13),
    "well_depth_measured_ft": 72,
    "electricity_tested": True,
    "signal_4g_tested": True,
    "sensors_calibrated": True,
    "farmer_training_done": True,
}


def _update(conn, table: str, cols: dict, where_sql: str, where_params: dict) -> int:
    sets = ", ".join(f"{c} = :{c}" for c in cols)
    params = {**cols, **where_params}
    res = conn.execute(text(f"UPDATE {table} SET {sets} WHERE {where_sql}"), params)
    return res.rowcount


def main() -> int:
    sync_url = os.environ.get("DATABASE_URL_SYNC")
    if not sync_url:
        print(
            "ERROR: DATABASE_URL_SYNC must be set (e.g. postgresql://agro:...@postgres:5432/agro)"
        )
        return 2
    eng = create_engine(sync_url, future=True)
    with eng.begin() as conn:
        n_t = _update(conn, "tenants", TENANTS, "id = :id", {"id": PILOT_TENANT})
        n_fa = _update(conn, "farmers", FARMERS, "farmer_id = :fid", {"fid": FARMER_ID})
        n_fm = _update(conn, "farms", FARMS, "farm_id = :fid", {"fid": FARM_ID})
        n_p = _update(conn, "plots", PLOTS, "plot_id = :pid", {"pid": PLOT_ID})
        n_cs = _update(
            conn,
            "crop_seasons",
            CROP_SEASON,
            "plot_id = :pid AND crop_name_english = 'Ginger' AND season_status = 'active'",
            {"pid": PLOT_ID},
        )
        n_dev = _update(
            conn, "device_registry", DEVICE_MAIN, "device_id = :did", {"did": MAIN_NODE_ID}
        )
        cols = ", ".join(TECH_INSTALL)
        ph = ", ".join(f":{c}" for c in TECH_INSTALL)
        upd = ", ".join(f"{c} = EXCLUDED.{c}" for c in TECH_INSTALL if c != "installation_id")
        conn.execute(
            text(
                f"INSERT INTO technician_installations ({cols}) VALUES ({ph}) "
                f"ON CONFLICT (installation_id) DO UPDATE SET {upd}"
            ),
            TECH_INSTALL,
        )

    print("pilot sheet loaded:")
    print(f"  tenants updated          : {n_t}")
    print(f"  farmers updated          : {n_fa}")
    print(f"  farms updated            : {n_fm}")
    print(f"  plots updated            : {n_p}  (PLOT_PILOT_001)")
    print(f"  crop_seasons updated     : {n_cs}  (active Ginger season)")
    print(f"  device_registry updated  : {n_dev}  (Main Node {MAIN_NODE_ID})")
    print("  technician_installations : 1 upserted")
    for label, n in (("farmer", n_fa), ("farm", n_fm), ("plot", n_p), ("season", n_cs)):
        if n == 0:
            print(f"  WARNING: 0 {label} rows matched — was the pilot seeded (seed_pilot)?")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
