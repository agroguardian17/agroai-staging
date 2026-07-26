# AgroGuardian V2

AgroGuardian is a precision-agriculture platform prototype for sensor-backed farm monitoring and farmer advisories. The active implementation is in [`agro_backend/`](agro_backend/): a FastAPI hexagonal monolith with PostgreSQL/PostGIS persistence, MQTT telemetry ingest, rule-based alerts, OTP/JWT authentication, and a Streamlit operations dashboard.

Start with the [codebase guide](agro_backend/docs/CODEBASE_GUIDE.md). It explains the architecture, runtime flows, database, rules, dashboard, deployment topology, and current limitations. The other operational references are:

- [API reference](agro_backend/docs/API_REFERENCE.md)
- [Development and operations guide](agro_backend/docs/DEVELOPMENT.md)
- [Hardware wire contract](agro_backend/docs/HARDWARE_WIRE_CONTRACT.md)
- [Schema decisions](agro_backend/docs/SCHEMA_DECISIONS.md)

The repository is proprietary. Do not commit `.env` files, provider credentials, JWT secrets, MQTT passwords, or service-account JSON files.
