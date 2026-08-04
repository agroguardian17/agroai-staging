"""Seed pilot data for the Aurangabad deployment.


Aggregate-mode hardware topology:


* **1 Main Node** (``AGR-MN-0001``, device_type = ``master_node``).
  Owns the MQTT credential. Aggregates LoRa frames from Sub Nodes and
  publishes to ``agro/v2/{tenant}/{farm}/{node}/telemetry`` on behalf
  of each Sub Node (the ``node_id`` in each MQTT payload identifies the
  originating Sub Node, not the Main Node).
* **2 Sub Nodes** (``AGR-SN-0001``, ``AGR-SN-0002``, device_type =
  ``sub_node``). Each Sub Node covers 2 plots.
* **4 Plots** (``PLOT_PILOT_001``..``004``).
  - Plots 001, 002 are covered by Sub Node 1.
  - Plots 003, 004 are covered by Sub Node 2.
* **1 Farmer**, **1 Farm**, **4 active crop seasons** (one per plot;
  ``compose_advisory`` requires an active season for context).


Idempotent: fixed UUIDs, so re-running upserts.


Backward compatibility: the pilot used to be seeded with a single device
``AGR-MH-0001`` mapped to ``PLOT_PILOT_001``. We keep an ON CONFLICT DO
NOTHING for those exact identifiers so old fake_main_node.py invocations
continue to work; the new devices are added alongside.


Run::


    set -a; source .env; set +a
    export DATABASE_URL_SYNC="postgresql://agro:$POSTGRES_PASSWORD@localhost:5433/agro"
    python scripts/dev/seed_pilot.py


Reads ``DATABASE_URL_SYNC`` from the shell. Prints the IDs at the end so
you can copy them into ``fake_main_node.py`` + the OTP curl + the Main
Node firmware config.
"""


from __future__ import annotations

import os
import sys
import uuid

from sqlalchemy import create_engine, text

PILOT_TENANT = "11111111-1111-1111-1111-111111111111"


# Stable identifiers - re-running won't multiply rows.
FARMER_ID = uuid.UUID("aaaaaaaa-1111-1111-1111-111111111111")
FARM_ID = uuid.UUID("bbbbbbbb-2222-2222-2222-222222222222")


# ----- Hardware identities (aggregate mode) -----
MAIN_NODE_ID = "AGR-MN-0001"
SUB_NODE_1_ID = "AGR-SN-0001"
SUB_NODE_2_ID = "AGR-SN-0002"


# ----- Backward-compat sub node (used by earlier tests + fake_main_node.py) -----
LEGACY_DEVICE_ID = "AGR-MH-0001"


# ----- Plots + seasons -----
# All 4 pilot plots grow ginger in the Kharif 2026 season. Variety and dates are
# placeholders until confirmed with the field team; correct them in place when
# you have the real values.
GINGER_VARIETY = "Mahima"
GINGER_SOWING_DATE = "2026-06-01"
GINGER_EXPECTED_HARVEST_DATE = "2027-02-01"

PLOTS = [
    # (plot_id, sub_node_device_id, season_id, crop_marathi, crop_english)
    ("PLOT_PILOT_001", SUB_NODE_1_ID, uuid.UUID("cccccccc-3333-3333-3333-000000000001"), "आले", "Ginger"),
    ("PLOT_PILOT_002", SUB_NODE_1_ID, uuid.UUID("cccccccc-3333-3333-3333-000000000002"), "आले", "Ginger"),
    ("PLOT_PILOT_003", SUB_NODE_2_ID, uuid.UUID("cccccccc-3333-3333-3333-000000000003"), "आले", "Ginger"),
    ("PLOT_PILOT_004", SUB_NODE_2_ID, uuid.UUID("cccccccc-3333-3333-3333-000000000004"), "आले", "Ginger"),
]


PHONE = os.environ.get("PILOT_PHONE", "+919999999999")




def main() -> int:
    sync_url = os.environ.get("DATABASE_URL_SYNC")
    if not sync_url:
        print(
            "ERROR: DATABASE_URL_SYNC must be set. Run:\n"
            "    set -a; source .env; set +a\n"
            '    export DATABASE_URL_SYNC="postgresql://agro:$POSTGRES_PASSWORD@localhost:5433/agro"',
            file=sys.stderr,
        )
        return 1


    eng = create_engine(sync_url, future=True)
    with eng.begin() as conn:
        # ---- Farmer ----
        conn.execute(
            text(
                """
                INSERT INTO farmers (
                    farmer_id, tenant_id, full_name, marathi_name, phone_primary,
                    whatsapp_number, language_preference, village, taluka, district,
                    state, subscription_tier, subscription_start, subscription_end,
                    payment_status
                ) VALUES (
                    :fid, :tenant, 'Pilot Farmer', 'पायलट शेतकरी', :phone,
                    :phone, 'marathi', 'Aurangabad-V', 'Aurangabad', 'Aurangabad',
                    'Maharashtra', 'basic', '2025-06-01', '2026-06-01', 'paid'
                )
                ON CONFLICT (farmer_id) DO UPDATE
                    SET phone_primary = EXCLUDED.phone_primary,
                        whatsapp_number = EXCLUDED.whatsapp_number
                """
            ),
            {"fid": FARMER_ID, "tenant": PILOT_TENANT, "phone": PHONE},
        )


        # ---- Farm ----
        conn.execute(
            text(
                """
                INSERT INTO farms (
                    farm_id, tenant_id, farmer_id, total_area_acre,
                    gps_lat_center, gps_lng_center, soil_type,
                    water_source_primary, irrigation_type, electricity_source
                ) VALUES (
                    :farm, :tenant, :farmer, 4.0, 19.9, 75.7, 'black',
                    'well', 'drip', 'grid'
                )
                ON CONFLICT (farm_id) DO NOTHING
                """
            ),
            {"farm": FARM_ID, "tenant": PILOT_TENANT, "farmer": FARMER_ID},
        )


        # ---- Legacy sub node (backward compat with older tests + fake_main_node.py) ----
        conn.execute(
            text(
                """
                INSERT INTO device_registry (
                    device_id, tenant_id, device_type, serial_number,
                    mac_address, qr_code_data, farm_id, device_tier,
                    installation_date, device_status
                ) VALUES (
                    :dev, :tenant, 'sub_node', 'SN-LEGACY-001',
                    'AA:BB:CC:DD:EE:01', 'QR_LEGACY_001', :farm, 'basic',
                    '2025-06-01', 'online'
                )
                ON CONFLICT (device_id) DO NOTHING
                """
            ),
            {"dev": LEGACY_DEVICE_ID, "tenant": PILOT_TENANT, "farm": FARM_ID},
        )


        # ---- Main Node (holds the MQTT credential) ----
        conn.execute(
            text(
                """
                INSERT INTO device_registry (
                    device_id, tenant_id, device_type, serial_number,
                    mac_address, qr_code_data, farm_id, device_tier,
                    installation_date, device_status
                ) VALUES (
                    :dev, :tenant, 'master_node', 'MN-PILOT-001',
                    'AA:BB:CC:DD:EE:MN', 'QR_MN_001', :farm, 'pro',
                    '2026-07-20', 'online'
                )
                ON CONFLICT (device_id) DO NOTHING
                """
            ),
            {"dev": MAIN_NODE_ID, "tenant": PILOT_TENANT, "farm": FARM_ID},
        )


        # ---- Sub Nodes (LoRa endpoints) ----
        for sub_id, mac_tail, serial_tail, qr_tail in [
            (SUB_NODE_1_ID, "S1", "SN-PILOT-01", "QR_SN_01"),
            (SUB_NODE_2_ID, "S2", "SN-PILOT-02", "QR_SN_02"),
        ]:
            conn.execute(
                text(
                    """
                    INSERT INTO device_registry (
                        device_id, tenant_id, device_type, serial_number,
                        mac_address, qr_code_data, farm_id, device_tier,
                        installation_date, device_status
                    ) VALUES (
                        :dev, :tenant, 'sub_node', :serial,
                        :mac, :qr, :farm, 'standard',
                        '2026-07-20', 'online'
                    )
                    ON CONFLICT (device_id) DO NOTHING
                    """
                ),
                {
                    "dev": sub_id,
                    "tenant": PILOT_TENANT,
                    "farm": FARM_ID,
                    "serial": serial_tail,
                    "mac": f"AA:BB:CC:DD:EE:{mac_tail}",
                    "qr": qr_tail,
                },
            )


        # ---- Plots + Crop Seasons ----
        for i, (plot_id, sub_dev, season_id, crop_mr, crop_en) in enumerate(PLOTS):
            conn.execute(
                text(
                    """
                    INSERT INTO plots (
                        plot_id, tenant_id, farm_id, plot_number, area_acre,
                        gps_lat, gps_lng, irrigation_valve_id, node_id
                    ) VALUES (
                        :plot, :tenant, :farm, :n, 1.0, 19.9, 75.7, :valve, :dev
                    )
                    ON CONFLICT (plot_id) DO NOTHING
                    """
                ),
                {
                    "plot": plot_id,
                    "tenant": PILOT_TENANT,
                    "farm": FARM_ID,
                    "n": i + 1,
                    "valve": f"V_{i + 1:03d}",
                    "dev": sub_dev,
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO crop_seasons (
                        season_id, tenant_id, farm_id, plot_id, season_name,
                        season_type, year, crop_name_marathi, crop_name_english,
                        crop_variety, crop_category, sowing_date, expected_harvest_date,
                        current_growth_stage, crop_age_days_today, season_status
                    ) VALUES (
                        :sid, :tenant, :farm, :plot, 'Kharif 2026 Ginger',
                        'kharif', 2026, :cmr, :cen,
                        :variety, 'cash_crop', :sowing, :harvest,
                        'vegetative', 50, 'active'
                    )
                    ON CONFLICT (season_id) DO NOTHING
                    """
                ),
                {
                    "sid": season_id,
                    "tenant": PILOT_TENANT,
                    "farm": FARM_ID,
                    "plot": plot_id,
                    "cmr": crop_mr,
                    "cen": crop_en,
                    "variety": GINGER_VARIETY,
                    "sowing": GINGER_SOWING_DATE,
                    "harvest": GINGER_EXPECTED_HARVEST_DATE,
                },
            )


    print()
    print("=========================================")
    print("Pilot data seeded successfully")
    print("=========================================")
    print(f"Tenant ID:     {PILOT_TENANT}")
    print(f"Farmer ID:     {FARMER_ID}")
    print(f"Farm ID:       {FARM_ID}")
    print(f"Phone:         {PHONE}")
    print()
    print("Devices (aggregate mode - Main Node owns MQTT credential):")
    print(f"  Main Node:   {MAIN_NODE_ID}    (master_node, pro tier)")
    print(f"  Sub Node 1:  {SUB_NODE_1_ID}   -> PLOT_PILOT_001, PLOT_PILOT_002")
    print(f"  Sub Node 2:  {SUB_NODE_2_ID}   -> PLOT_PILOT_003, PLOT_PILOT_004")
    print(f"  Legacy:      {LEGACY_DEVICE_ID}   (unchanged; older tests + fake_main_node.py)")
    print()
    print("Plots + crops:")
    for plot_id, sub_dev, _sid, cmr, cen in PLOTS:
        print(f"  {plot_id} -> {sub_dev}  crop={cen} ({cmr})")
    print()
    print("MQTT topic pattern (Main Node publishes on behalf of Sub Nodes):")
    print(f"  agro/v2/{PILOT_TENANT}/{FARM_ID}/<sub_node_id>/telemetry")
    print()
    print("Auth: /auth/send_otp body: {{'phone':'" + PHONE + "'}}")
    return 0




if __name__ == "__main__":
    raise SystemExit(main())
