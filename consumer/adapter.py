#!/usr/bin/env python3
"""
Project Factory — Prompt Maker consumer adapter (FACTORY_CONSUMER_SUBSET_V1).

Prompt Maker is the PRODUCER-contract authority; this module is the CONSUMER implementation.
It consumes a ProjectBlueprintV1 (schema 1.1) -- or its consumer subset -- and either
  * returns one of five frozen outcomes without touching the filesystem, or
  * (for MATERIALIZATION_READY) materializes a real project from the exact Factory profile.

Frozen outcomes:
  MATERIALIZATION_READY | BLOCKED_REQUIRES_TECHNOLOGY_DECISION |
  BLOCKED_UNSUPPORTED_TECHNOLOGY_PROFILE | INVALID_BLUEPRINT | UNSUPPORTED_BLUEPRINT_SCHEMA

Hard rules (never relaxed here):
  * only technology_decision.status == CONFIRMED may materialize;
  * the stack is NEVER inferred from project_profiles / architecture_target / free text;
  * 'generic' is never a fallback and is not reachable through the mapping;
  * no fuzzy / closest / substitute matching -- only the pinned PROFILE_MAPPING_V1;
  * existing files in the output directory are never overwritten (no-clobber);
  * pinned contract files are SHA-256 verified before use (fail closed, raises PinIntegrityError).

Stdlib only.
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
from datetime import date as _date
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent.parent
PIN_DIR = FACTORY_DIR / "consumer" / "pin"
PROFILES_DIR = FACTORY_DIR / "profiles"

sys.path.insert(0, str(FACTORY_DIR))
import substitute  # noqa: E402  (shared token engine)

OUT_READY = "MATERIALIZATION_READY"
OUT_NEEDS_DECISION = "BLOCKED_REQUIRES_TECHNOLOGY_DECISION"
OUT_UNSUPPORTED_PROFILE = "BLOCKED_UNSUPPORTED_TECHNOLOGY_PROFILE"
OUT_INVALID = "INVALID_BLUEPRINT"
OUT_UNSUPPORTED_SCHEMA = "UNSUPPORTED_BLUEPRINT_SCHEMA"
OUTCOMES = (OUT_READY, OUT_NEEDS_DECISION, OUT_UNSUPPORTED_PROFILE, OUT_INVALID, OUT_UNSUPPORTED_SCHEMA)
EXIT_CODES = {OUT_READY: 0, OUT_NEEDS_DECISION: 10, OUT_UNSUPPORTED_PROFILE: 11, OUT_INVALID: 12, OUT_UNSUPPORTED_SCHEMA: 13}

SUPPORTED_SCHEMAS = ("1.1",)
SUBSET_FIELDS = (
    "schema_version", "project_name", "project_goal", "project_profiles", "target_platforms",
    "architecture_target", "technology_decision", "production_readiness_target",
    "required_decisions", "prohibited_shortcuts",
)
STATUSES = ("CONFIRMED", "REQUIRES_DECISION", "NOT_APPLICABLE_WITH_RATIONALE", "DEFERRED_WITH_GATE")
SOURCE_TYPES = ("USER_CONFIRMED", "PROFILE", "RULE", "INFERRED_DEFAULT", None)

# Properties of the Factory's own profiles (what the profile IS), not an inference from the blueprint.
PROFILE_PROPERTIES = {
    "react-vite-supabase": {"project_type": "web"},
    "flutter-supabase": {"project_type": "mobile"},
}

PROVENANCE_FILE = "docs/ai/MATERIALIZATION_PROVENANCE.json"
SUBSET_FILE = "docs/ai/BLUEPRINT_CONSUMER_SUBSET.json"


class PinIntegrityError(RuntimeError):
    """A pinned producer file does not match its recorded SHA-256 (fail closed)."""


class MaterializationError(RuntimeError):
    """Materialization could not be completed safely (distinct from the five decision outcomes)."""


# ----------------------------------------------------------------------------- hashing / pin

def sha256_lf(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def canonical_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_pin(verify=True):
    pin = json.loads((PIN_DIR / "producer_pin.json").read_text(encoding="utf-8"))
    if verify:
        for rel, expected in pin["files"].items():
            actual = sha256_lf((FACTORY_DIR / rel).read_bytes())
            if actual != expected:
                raise PinIntegrityError("pinned file %s sha256 %s != recorded %s" % (rel, actual, expected))
        for key, rel in (("golden_fixture_sha256", "tests/fixtures/prompt-maker/golden-react-vite-supabase.json"),
                         ("profile_mapping_sha256", "consumer/pin/profile-mapping-v1.json"),
                         ("consumer_schema_sha256", "consumer/pin/consumer-subset-v1.schema.json")):
            if pin[key] != pin["files"][rel]:
                raise PinIntegrityError("%s disagrees with files[%s]" % (key, rel))
    return pin


def load_mapping():
    """Loads PROFILE_MAPPING_V1 only after SHA-256 verification of the pin."""
    load_pin(verify=True)
    return json.loads((PIN_DIR / "profile-mapping-v1.json").read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------- decision

def _obj(v):
    return isinstance(v, dict)


def _str(v):
    return isinstance(v, str)


def _ne(v):
    return isinstance(v, str) and v.strip() != ""


_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_CTRL_NO_NL = re.compile(r"[\x00-\x1f\x7f]")


def extract_subset(blueprint):
    """Deterministic projection: only the named fields, deep-copied; '_' and unknown fields ignored."""
    if not _obj(blueprint):
        return None
    return {k: json.loads(json.dumps(blueprint[k])) for k in SUBSET_FIELDS if k in blueprint}


def validate_subset(s):
    errors = []
    if not _ne(s.get("project_name")):
        errors.append("project_name")
    elif _CTRL_NO_NL.search(s["project_name"]):
        errors.append("project_name:control_characters")
    if not _ne(s.get("project_goal")):
        errors.append("project_goal")
    elif _CTRL.search(s["project_goal"]):
        errors.append("project_goal:control_characters")
    pp = s.get("project_profiles")
    if not (isinstance(pp, list) and all(_obj(p) and _ne(p.get("profile_id")) for p in pp)):
        errors.append("project_profiles")
    tp = s.get("target_platforms")
    if not (isinstance(tp, list) and all(_str(x) for x in tp)):
        errors.append("target_platforms")
    at = s.get("architecture_target")
    if not (_obj(at) and _ne(at.get("pattern")) and _ne(at.get("source"))):
        errors.append("architecture_target")
    t = s.get("technology_decision")
    if not _obj(t):
        errors.append("technology_decision")
    else:
        if t.get("status") not in STATUSES:
            errors.append("technology_decision.status")
        if not (t.get("stack") is None or _str(t.get("stack"))):
            errors.append("technology_decision.stack")
        if "source_type" not in t or t["source_type"] not in SOURCE_TYPES:
            errors.append("technology_decision.source_type")
        if not (t.get("profile_hint") is None or _str(t.get("profile_hint"))):
            errors.append("technology_decision.profile_hint")
        if not _str(t.get("rationale")):
            errors.append("technology_decision.rationale")
        if t.get("status") == "CONFIRMED" and not (_ne(t.get("stack")) and t.get("source_type") == "USER_CONFIRMED"):
            errors.append("technology_decision.CONFIRMED_requires_user_confirmed_stack")
    pr = s.get("production_readiness_target")
    if not (_obj(pr) and _str(pr.get("note")) and isinstance(pr.get("domains_covered"), list)
            and all(_str(x) for x in pr["domains_covered"])):
        errors.append("production_readiness_target")
    rd = s.get("required_decisions")
    if not (isinstance(rd, list) and all(_obj(x) for x in rd)):
        errors.append("required_decisions")
    ps = s.get("prohibited_shortcuts")
    if not (isinstance(ps, list) and all(_str(x) for x in ps)):
        errors.append("prohibited_shortcuts")
    return errors


def canonical_key(stack):
    return " ".join(stack.split()).lower()


def resolve_profile(stack, mapping):
    """Exact / documented-alias equality ONLY. No substring, prefix, similarity or fallback."""
    key = canonical_key(stack)
    for p in mapping["profiles"]:
        if key == p["profile_id"].lower():
            return "SUPPORTED_EXACT", p["profile_id"]
        if any(canonical_key(a) == key for a in p["aliases"]):
            return "SUPPORTED_ALIAS", p["profile_id"]
    return "UNSUPPORTED", None


def evaluate(blueprint, mapping=None):
    """INPUT -> SCHEMA CHECK -> SUBSET VALIDATION -> technology_decision -> PROFILE MAPPING.
    Pure: no filesystem writes. Returns a dict with 'outcome'."""
    mapping = mapping or load_mapping()
    subset = extract_subset(blueprint)
    if subset is None:
        return {"outcome": OUT_INVALID, "errors": ["blueprint must be a JSON object"]}
    sv = subset.get("schema_version")
    if not _ne(sv):
        return {"outcome": OUT_INVALID, "errors": ["schema_version"]}
    if sv not in SUPPORTED_SCHEMAS:
        return {"outcome": OUT_UNSUPPORTED_SCHEMA, "errors": ["schema_version %s" % sv]}
    errors = validate_subset(subset)
    if errors:
        return {"outcome": OUT_INVALID, "errors": errors}
    t = subset["technology_decision"]
    if t["status"] != "CONFIRMED":
        return {"outcome": OUT_NEEDS_DECISION, "classification": "REQUIRES_DECISION", "errors": [], "subset": subset}
    cls, profile = resolve_profile(t["stack"], mapping)
    if cls == "UNSUPPORTED":
        return {"outcome": OUT_UNSUPPORTED_PROFILE, "classification": cls, "errors": [], "subset": subset}
    return {"outcome": OUT_READY, "classification": cls, "profile": profile, "errors": [], "subset": subset}


# ----------------------------------------------------------------------------- materialization

def derive_slugs(name):
    """Same derivation as generate.sh (ASCII only; Arabic-only names fall back to my_project)."""
    raw = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not raw:
        raw = "my_project"
    if raw[0].isdigit():
        raw = "p_" + raw
    cls = "".join(part.capitalize() for part in raw.split("_") if part) or "MyProject"
    return raw, raw.replace("_", "-"), cls


def _escape_for(rel, value):
    """USER_INPUT != TRUSTED_CODE/HTML: escape token values for the syntax of the target file."""
    name = rel.lower()
    if name.endswith((".html", ".htm")):
        return html.escape(value, quote=True)
    if name.endswith((".ts", ".tsx", ".js", ".jsx")):
        return json.dumps(value, ensure_ascii=False)[1:-1].replace("<", "\\u003c")
    if name.endswith(".dart"):
        return (value.replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$")
                .replace("\n", "\\n").replace("\r", "\\r"))
    if name.endswith((".yaml", ".yml", ".json")):
        return json.dumps(value, ensure_ascii=False)[1:-1]
    return value


_TOKEN_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


def _apply_tokens(rel, text, tokens):
    """Single pass: a substituted value is never re-scanned (no token injection through user input)."""
    def repl(m):
        key = m.group(1)
        if key not in tokens:
            raise MaterializationError("unknown template token {{%s}} in %s" % (key, rel))
        return _escape_for(rel, tokens[key])
    return _TOKEN_RE.sub(repl, text)


def _collect_sources(profile):
    """dest-relative-path -> source Path. docs: generic first, profile overlays; then scaffold."""
    files = {}
    for base in (PROFILES_DIR / "generic" / "docs" / "ai", PROFILES_DIR / profile / "docs" / "ai"):
        if base.is_dir():
            for p in sorted(base.rglob("*")):
                if p.is_file():
                    files["docs/ai/" + p.relative_to(base).as_posix()] = p
    scaffold = PROFILES_DIR / profile / "scaffold"
    if scaffold.is_dir():
        for p in sorted(scaffold.rglob("*")):
            if p.is_file():
                files[p.relative_to(scaffold).as_posix()] = p
    return files


SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"sk_(live|test)_[A-Za-z0-9]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"(?i)service_role[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-.]{20,}"),
]


def scan_secrets(rel, text):
    return [rel for pat in SECRET_PATTERNS if pat.search(text)]


def _inside(child, parent):
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def materialize(blueprint, output_dir, *, project_date=None, owner=None, status="تخطيط", mapping=None):
    """Decision first; filesystem is touched ONLY for MATERIALIZATION_READY."""
    decision = evaluate(blueprint, mapping)
    if decision["outcome"] != OUT_READY:
        return {"outcome": decision["outcome"], "classification": decision.get("classification"),
                "errors": decision.get("errors", []), "materialized": False, "created": [], "skipped_existing": []}

    subset, profile = decision["subset"], decision["profile"]
    if not (PROFILES_DIR / profile).is_dir() or profile == "generic":
        raise MaterializationError("mapped profile %r has no Factory profile directory (or is generic)" % profile)

    out = Path(output_dir).expanduser().resolve()
    if _inside(out, FACTORY_DIR):
        raise MaterializationError("refusing to materialize inside the Factory source tree")
    pin = load_pin(verify=True)

    slug_snake, slug_kebab, cls_name = derive_slugs(subset["project_name"])
    cfg = {
        "PROJECT_NAME": subset["project_name"],
        "PROJECT_TYPE": PROFILE_PROPERTIES[profile]["project_type"],
        "PROJECT_STATUS": status,
        "PROJECT_OWNER": owner or "[المسؤول]",
        "PROJECT_DATE": project_date or _date.today().isoformat(),
        "PROJECT_GOAL": subset["project_goal"],
        "PROFILE_NAME": profile,
        "FACTORY_VERSION": (FACTORY_DIR / "VERSION").read_text(encoding="utf-8").strip(),
        "DB_SHARED": False,
        "RELATED_SYSTEMS": [],
        "SLUG_SNAKE": slug_snake, "SLUG_KEBAB": slug_kebab, "CLASS_NAME": cls_name,
    }
    tokens = substitute.build_tokens(cfg)

    sources = _collect_sources(profile)
    out.mkdir(parents=True, exist_ok=True)
    out_real = out.resolve()

    # Pre-flight: every template token must be known BEFORE any write.
    rendered = {}
    for rel, src in sources.items():
        try:
            text = src.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            rendered[rel] = (None, src.read_bytes())
            continue
        rendered[rel] = (_apply_tokens(rel, text, tokens), None)

    created, skipped = [], []
    hashes = {}
    for rel in sorted(rendered):
        dest = out / rel
        if not _inside(dest.parent.resolve(), out_real):
            raise MaterializationError("path escapes output directory: " + rel)
        if dest.exists() or dest.is_symlink():
            skipped.append(rel)               # NO-CLOBBER
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        text, raw = rendered[rel]
        if text is not None:
            dest.write_bytes(text.encode("utf-8"))
        else:
            dest.write_bytes(raw)
        created.append(rel)
        hashes[rel] = sha256_lf(dest.read_bytes())

    # source provenance (no-clobber too)
    subset_text = json.dumps(subset, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    prov = {
        "provenance_version": 1,
        "outcome": OUT_READY,
        "classification": decision["classification"],
        "profile": profile,
        "technology_stack_as_declared": subset["technology_decision"]["stack"],
        "factory_version": cfg["FACTORY_VERSION"],
        "producer_repository": pin["producer_repository"],
        "producer_contract_commit": pin["producer_contract_commit"],
        "project_blueprint_schema": subset["schema_version"],
        "consumer_subset_version": pin["consumer_subset_version"],
        "profile_mapping_sha256": pin["profile_mapping_sha256"],
        "consumer_schema_sha256": pin["consumer_schema_sha256"],
        "blueprint_subset_sha256": sha256_lf(subset_text),
        "materialization_date": cfg["PROJECT_DATE"],
        "files": {k: hashes[k] for k in sorted(hashes)},
        "scope_note": "Starting-project package only. Blueprint/contract is NOT execution authority; "
                      "ACCEPTANCE_TARGET != ACCEPTANCE_EVIDENCE; PRODUCTION_TARGET != PRODUCTION_CERTIFICATION.",
    }
    for rel, content in ((SUBSET_FILE, subset_text), (PROVENANCE_FILE, json.dumps(prov, ensure_ascii=False, indent=2) + "\n")):
        dest = out / rel
        if dest.exists() or dest.is_symlink():
            skipped.append(rel)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        created.append(rel)

    validation = validate_materialized(out, profile, sources, cfg, created)
    return {
        "outcome": OUT_READY, "classification": decision["classification"], "profile": profile,
        "errors": [], "materialized": True, "output_dir": str(out),
        "created": created, "skipped_existing": skipped, "validation": validation,
        "status": "MATERIALIZED_AND_VALIDATED" if validation["ok"] else "MATERIALIZED_VALIDATION_FAILED",
    }


def validate_materialized(out, profile, sources, cfg, created):
    """Validates the generated project; never reports ok on missing evidence."""
    problems = []
    for rel in list(sources) + [SUBSET_FILE, PROVENANCE_FILE]:
        if not (out / rel).is_file():
            problems.append("missing expected file: " + rel)
    # secret residue only over files this run created
    for rel in created:
        p = out / rel
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for hit in scan_secrets(rel, text):
            problems.append("secret-like pattern in " + hit)
    created_set = set(created)
    if profile == "react-vite-supabase" and "package.json" in created_set:
        try:
            pkg = json.loads((out / "package.json").read_text(encoding="utf-8"))
            if pkg.get("name") != cfg["SLUG_KEBAB"]:
                problems.append("package.json name %r != %r" % (pkg.get("name"), cfg["SLUG_KEBAB"]))
            for k in ("scripts", "dependencies"):
                if not isinstance(pkg.get(k), dict) or not pkg[k]:
                    problems.append("package.json missing " + k)
        except ValueError as e:
            problems.append("package.json invalid JSON: %s" % e)
    if profile == "flutter-supabase" and "pubspec.yaml" in created_set:
        m = re.match(r"name:\s*(\S+)", (out / "pubspec.yaml").read_text(encoding="utf-8"))
        if not m or m.group(1) != cfg["SLUG_SNAKE"]:
            problems.append("pubspec.yaml name mismatch")
    return {"ok": not problems, "problems": problems}


# ----------------------------------------------------------------------------- CLI

def _load_blueprint_file(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "__UNPARSEABLE__"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Prompt Maker blueprint consumer (FACTORY_CONSUMER_SUBSET_V1)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("evaluate", help="decide the outcome; writes nothing")
    e.add_argument("--blueprint", required=True)
    m = sub.add_parser("materialize", help="materialize iff MATERIALIZATION_READY")
    m.add_argument("--blueprint", required=True)
    m.add_argument("--output", required=True)
    m.add_argument("--date")
    m.add_argument("--owner")
    a = ap.parse_args(argv)
    bp = _load_blueprint_file(a.blueprint)
    if bp == "__UNPARSEABLE__":
        print(json.dumps({"outcome": OUT_INVALID, "errors": ["unreadable or non-JSON blueprint"]}, ensure_ascii=False))
        return EXIT_CODES[OUT_INVALID]
    if a.cmd == "evaluate":
        r = evaluate(bp)
        r.pop("subset", None)
    else:
        r = materialize(bp, a.output, project_date=a.date, owner=a.owner)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    if r.get("materialized") and r.get("status") != "MATERIALIZED_AND_VALIDATED":
        return 20
    return EXIT_CODES[r["outcome"]]


if __name__ == "__main__":
    sys.exit(main())
