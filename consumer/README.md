# Prompt Maker consumer adapter (FACTORY_CONSUMER_SUBSET_V1)

**Authority split.** Prompt Maker (`firasfanon/Palwakf_Prompt_Maker`) is the *producer-contract* authority.
This directory is the *consumer implementation*. Everything under `consumer/pin/` and
`tests/fixtures/prompt-maker/` is a **pinned copy / test input, not contract authority**; the pin is verified by
SHA-256 before every evaluation and a mismatch raises `PinIntegrityError` (fail closed).

Pin: `producer_contract_commit f659f92d34449f093de05be6cc52a7f6c5221c84`, `project_blueprint_schema 1.1`,
`consumer_subset_version 1`, `fixture_version 1` (see `consumer/pin/producer_pin.json`).
To upgrade, re-vendor from a newer accepted Prompt Maker commit, update the pin and the tests together.

## Use
```
python3 consumer/adapter.py evaluate    --blueprint bp.json                 # writes nothing
python3 consumer/adapter.py materialize --blueprint bp.json --output DIR [--date YYYY-MM-DD] [--owner NAME]
```
Exit codes: 0 `MATERIALIZATION_READY`, 10 `BLOCKED_REQUIRES_TECHNOLOGY_DECISION`,
11 `BLOCKED_UNSUPPORTED_TECHNOLOGY_PROFILE`, 12 `INVALID_BLUEPRINT`, 13 `UNSUPPORTED_BLUEPRINT_SCHEMA`,
20 materialized but post-validation failed.

## Rules
- Only `technology_decision.status == CONFIRMED` (with `source_type USER_CONFIRMED`) can materialize.
- Stack -> profile uses only the pinned `PROFILE_MAPPING_V1` (exact or documented alias). No inference from
  `project_profiles`/`architecture_target`/text, no fuzzy match, no `generic` fallback, no substitution.
- Blocked/invalid outcomes touch no filesystem.
- No-clobber: existing files (and symlinks) in the output directory are never overwritten; the run is idempotent.
- Refuses an output directory inside the Factory tree. Does not write `PROJECTS_REGISTRY.md` (no side effects on the Factory).
- Token values are escaped per target syntax (HTML / TS / Dart / YAML / JSON) and substituted in a single pass.
- Output includes `docs/ai/BLUEPRINT_CONSUMER_SUBSET.json` and `docs/ai/MATERIALIZATION_PROVENANCE.json`
  (producer commit, mapping/schema SHA-256, per-file SHA-256). A materialized package is a *starting project*:
  Blueprint/contract is not execution authority and passing materialization is not production readiness.
- Values not in the blueprint subset use explicit defaults: status `تخطيط`, owner `[المسؤول]`, `DB_SHARED=false`,
  `PROJECT_TYPE` taken from the selected Factory profile (web / mobile).

## Tests
`python3 -m unittest discover -s tests -v` (stdlib only, Linux and Git Bash/Windows). Includes a legacy `generate.sh` equivalence test against the base commit and an injection security regression with a control experiment (set `FACTORY_TEST_BASH` to override Bash discovery).
Not covered here: `npm install/build/test` of the generated project (requires registry access) -- see CHANGELOG.
