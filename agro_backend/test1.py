# scratch/run_ingest.py - or paste this into a python repl
import asyncio, os
from app.application.ingest_telemetry import IngestDeps
from app.infra.mqtt.broker import BrokerSettings, IngestBroker
from app.infra.persistence.engine import make_async_engine, make_sessionmaker
from app.infra.persistence.pg_reading_repo import PgReadingRepo
from app.infra.events.pg_notify_bus import PgNotifyEventBus


async def main():
    eng = make_async_engine(os.environ["DATABASE_URL"])
    sm = make_sessionmaker(eng)
    deps = IngestDeps(
        reading_repo=PgReadingRepo(sm),
        event_bus=PgNotifyEventBus(sm),
    )
    broker = IngestBroker(BrokerSettings(host="localhost", port=1883), deps)
    await broker.start()
    print("ingest worker running; Ctrl-C to stop")
    try:
        await asyncio.sleep(3600)  # 1 hour
    except KeyboardInterrupt:
        pass
    finally:
        await broker.stop()
        await eng.dispose()


asyncio.run(main())