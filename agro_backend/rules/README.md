# rules

This directory is intentionally present because the Docker image copies it and
the project architecture reserves it for future data-driven rules.

The active pilot rules are currently Python code in
`app/domain/rule_definitions.py`, evaluated by `app/domain/rules.py`. There are
no YAML/JSON rule files here today. Do not add a second rule source without
defining precedence, validation, tests, and a migration/versioning policy.
