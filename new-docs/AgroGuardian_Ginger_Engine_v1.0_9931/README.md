# Agro-Guardian AI — Ginger Advisory Engine

Read `ARCHITECTURE.md` first. It explains why the design is the way it is,
including three bugs that shaped it and that unit tests could not see.

## Seven files run in production

    engine/trigger_dsl.py          parser, three-valued evaluator
    engine/precedence.py           conflict resolution + diagnosis
    engine/notification_policy.py  delivery behaviour
    engine/expert_override.py      override API + refusals
    engine/persistence.py          state across restarts
    engine/runner.py               entry point, message composition
    engine/runtime_loader.py       loads rules from the DATABASE

Plus the loaded knowledge base: generated/agroguardian_ginger_kb.sql

Everything in authoring/, build/ and tests/ stays out of the deployment.
See ARCHITECTURE.md §11A for why runtime_loader.py matters.

## Layout

    engine/           7 files — deploy these
    authoring/        3 files — how a human writes a trigger
    build/            4 files — JSON -> SQL, classification, simulation
    tests/            7 files — regression gate and suites
    knowledge_base/  13 JSON  — THE SOURCE OF TRUTH
    generated/        1 SQL   — DO NOT EDIT
    docs/             expert review sheet

## Run

Scripts expect a flat working directory. Flatten, or set PYTHONPATH.

    python3 regression_gate.py                 # must pass first
    python3 json_to_sql.py --out kb.sql
    psql -d agroguardian -f kb.sql

## Try it

    python3 runner.py --case all --internals   # what a farmer reads
    python3 simulate_season.py --scenario all  # 240 days, 5 scenarios
    python3 runtime_loader.py                  # build vs DB, side by side

## Change a rule

Edit the JSON in knowledge_base/. Run the gate. Regenerate the SQL.
Never edit the SQL. Never edit the .py trigger files expecting production
to pick it up — production reads the database.

## Four things that will cost you time if you skip them

  §3   UNKNOWN is not FALSE. A missing sensor reading must not suppress an alert.
  §4   Do not rank by severity. Use kb_precedence.
  §5   A trigger is a condition; the advice is an event. Use the delivery class.
  §11A Production reads the database, not the build files.

And do not sum kb_rules.u_value — use v_u_values_deduplicated. Thirteen
factors appear in more than one domain.
