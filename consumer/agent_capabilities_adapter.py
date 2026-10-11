"""Agent-capabilities handoff consumer, independent of the frozen Factory adapter.

Reads and verifies the Prompt Maker reference sidecar and optionally an external
Visual QA report. Does NOT invoke agents, load skills, install packages, authorize
writes outside the requested new output, or imply production acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import adapter

CONTRACT = "PM_FACTORY_AGENT_CAPABILITIES_HANDOFF_V1"
STATUS = "REFERENCE_ATTACHED_NOT_RUNTIME_ADMITTED"
MAX_JSON_BYTES = 3 * 1024 * 1024


def read_bounded_json(path, max_bytes=MAX_JSON_BYTES):
    p = Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size > max_bytes:
        raise ValueError("INVALID_OR_OVERSIZED_INPUT_FILE")
    raw = p.read_bytes()
    return raw, json.loads(raw.decode("utf-8-sig"))


def is_dict(x):
    return isinstance(x, dict)


def require_keys(obj, keys, label):
    if not is_dict(obj) or set(obj) != set(keys):
        raise ValueError("INVALID_" + label + "_KEYS")


def validate_handoff(blueprint, blueprint_bytes, h):
    require_keys(h, ("contract_id", "schema_version", "producer", "authority",
                     "ui_ux_design", "skills_selection", "visual_qa_feedback", "materialization"), "HANDOFF")
    if h["contract_id"] != CONTRACT or h["schema_version"] != "1.0":
        raise ValueError("UNSUPPORTED_HANDOFF_CONTRACT")
    producer = h["producer"]
    require_keys(producer, ("product_id", "blueprint_schema_version",
                            "blueprint_sha256", "project_name"), "PRODUCER")
    if (producer["product_id"] != "PROMPT_MAKER"
        or producer["blueprint_schema_version"] != "1.1"
        or producer["blueprint_sha256"] != hashlib.sha256(blueprint_bytes).hexdigest()
        or producer["project_name"] != blueprint.get("project_name")):
        raise ValueError("BLUEPRINT_IDENTITY_MISMATCH")
    auth = h["authority"]
    require_keys(auth, ("product", "materialization", "agent_runtime",
                        "authorization", "runtime_admission", "execution_authorized"), "AUTHORITY")
    if auth != {
        "product": "PROMPT_MAKER", "materialization": "PROJECT_FACTORY",
        "agent_runtime": "AGENTIC", "authorization": "WORKSPACE",
        "runtime_admission": False, "execution_authorized": False
    }:
        raise ValueError("UNAUTHORIZED_AGENT_CAPABILITY")
    ui = h["ui_ux_design"]
    require_keys(ui, ("status", "agent", "required_review", "product_surfaces",
                       "target_platforms", "confirmed_design_references", "output_claim"), "DESIGN")
    if (ui["status"] != "REFERENCE_REQUEST_ONLY" or ui["agent"] != "UI_UX_DESIGNER"
        or ui["required_review"] is not True or ui["output_claim"] != "NOT_GENERATED"
        or ui["product_surfaces"] != blueprint.get("product_surfaces")
        or ui["target_platforms"] != blueprint.get("target_platforms")
        or not isinstance(ui["confirmed_design_references"], list)
        or any(not isinstance(x, str) or len(x) > 5000 for x in ui["confirmed_design_references"])):
        raise ValueError("INVALID_DESIGN_REFERENCE")
    expected_design_refs = [
        x["value"][:5000]
        for x in blueprint.get("confirmed_requirements", [])
        if is_dict(x) and x.get("field") == "design_references"
        and x.get("status") == "CONFIRMED" and isinstance(x.get("value"), str)
    ]
    if ui["confirmed_design_references"] != expected_design_refs:
        raise ValueError("DESIGN_REFERENCE_NOT_SOURCE_DERIVED")
    skills = h["skills_selection"]
    require_keys(skills, ("status", "capability", "runtime_admitted", "source_class",
                          "request", "selected_skills"), "SKILLS")
    if (skills["status"] != "NOT_INVOKED" or skills["capability"] != "skills.select.read_only"
        or skills["runtime_admitted"] is not False
        or skills["source_class"] != "SOVEREIGN_INTERNAL_PRIORITY"
        or skills["selected_skills"] != []):
        raise ValueError("SKILLS_EXECUTION_OR_FALSE_SELECTION_CLAIM")
    request = skills["request"]
    require_keys(request, ("task_id", "description", "scope", "requested_mode"), "SKILLS_REQUEST")
    expected_task = "pmref_" + hashlib.sha256(blueprint_bytes).hexdigest()[:24]
    if request != {
        "task_id": expected_task,
        "description": "UI UX accessibility design review engineering reference",
        "scope": "engineering_reference",
        "requested_mode": "read_only_reference",
    }:
        raise ValueError("SKILLS_REQUEST_MISMATCH")
    qa = h["visual_qa_feedback"]
    require_keys(qa, ("status", "reviewed_by_agent", "findings",
                      "evidence", "acceptance_authority"), "QA")
    if qa != {
        "status": "NOT_RUN", "reviewed_by_agent": False,
        "findings": [], "evidence": [],
        "acceptance_authority": "WORKSPACE_NOT_DELEGATED",
    }:
        raise ValueError("UNVERIFIED_VISUAL_QA_CLAIM")
    mat = h["materialization"]
    require_keys(mat, ("status", "candidate_only", "production_ready"), "MATERIALIZATION")
    if mat != {
        "status": "FACTORY_CONSUMER_TO_DECIDE",
        "candidate_only": True, "production_ready": False,
    }:
        raise ValueError("UNAUTHORIZED_PRODUCTION_CLAIM")


def parse_feedback(value):
    if value is None:
        return {
            "status": "NOT_PROVIDED", "reviewed_by_agent": False,
            "findings": [], "evidence": [], "acceptance_authority": "NOT_DELEGATED"
        }
    require_keys(value, ("schema_version", "status", "findings", "evidence"), "EXTERNAL_FEEDBACK")
    if value["schema_version"] != "1.0" or value["status"] != "REPORT_AVAILABLE":
        raise ValueError("INVALID_VISUAL_QA_FEEDBACK_STATUS")
    findings = value["findings"]
    evidence = value["evidence"]
    if (not isinstance(findings, list) or len(findings) > 100
        or not all(isinstance(x, str) and len(x) <= 1000 for x in findings)
        or not isinstance(evidence, list) or not (1 <= len(evidence) <= 100)):
        raise ValueError("INVALID_VISUAL_QA_EVIDENCE")
    for item in evidence:
        require_keys(item, ("reference", "sha256"), "QA_EVIDENCE")
        if (not isinstance(item["reference"], str) or not 1 <= len(item["reference"]) <= 512
            or not isinstance(item["sha256"], str)
            or re.fullmatch(r"[0-9a-fA-F]{64}", item["sha256"]) is None):
            raise ValueError("INVALID_VISUAL_QA_EVIDENCE_ENTRY")
    return {
        "status": "UNVERIFIED_EXTERNAL_REPORT",
        "reviewed_by_agent": False,
        "findings": findings,
        "evidence": evidence,
        "acceptance_authority": "NOT_DELEGATED"
    }


def deliver(blueprint_file, handoff_file, output_dir, feedback_file=None):
    blueprint_raw, blueprint = read_bounded_json(blueprint_file)
    handoff_raw, handoff = read_bounded_json(handoff_file)
    validate_handoff(blueprint, blueprint_raw, handoff)
    feedback = parse_feedback(read_bounded_json(feedback_file, 1024 * 1024)[1]
                              if feedback_file else None)
    decision = adapter.evaluate(blueprint)
    if decision["outcome"] != adapter.OUT_READY:
        return {"outcome": decision["outcome"], "materialized": False,
                "agent_capabilities_status": "NOT_ATTACHED",
                "errors": decision.get("errors", [])}
    output = Path(output_dir).expanduser()
    # Strict new destination: protect existing projects, symlinks and files.
    if output.exists() or output.is_symlink():
        raise ValueError("OUTPUT_ALREADY_EXISTS_NO_CLOBBER")
    result = adapter.materialize(blueprint, output)
    if not result.get("materialized") or result.get("status") != "MATERIALIZED_AND_VALIDATED":
        return result
    out = Path(result["output_dir"]) / "docs" / "ai"
    reference_file = out / "AGENT_CAPABILITIES_REFERENCE_V1.json"
    provenance_file = out / "AGENT_CAPABILITIES_REFERENCE_PROVENANCE_V1.json"
    sidecar = {
        "contract_id": CONTRACT,
        "status": STATUS,
        "handoff": handoff,
        "visual_qa_external_feedback": feedback,
        "execution": False, "production_ready": False,
    }
    reference_bytes = (json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    provenance = {
        "status": STATUS,
        "blueprint_sha256": hashlib.sha256(blueprint_raw).hexdigest(),
        "handoff_sha256": hashlib.sha256(handoff_raw).hexdigest(),
        "reference_sha256": hashlib.sha256(reference_bytes).hexdigest(),
        "evidence_is_not_runtime_admission": True,
    }
    with reference_file.open("xb") as stream:
        stream.write(reference_bytes)
    with provenance_file.open("xb") as stream:
        stream.write((json.dumps(provenance, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return {
        "outcome": result["outcome"], "materialized": True,
        "profile": result["profile"], "agent_capabilities_status": STATUS,
        "visual_qa_status": feedback["status"],
        "output_dir": result["output_dir"],
        "reference_sha256": provenance["reference_sha256"],
        "runtime_admission": False, "execution": False, "production_ready": False,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Reference-only agent handoff consumer; never runs agents")
    ap.add_argument("--blueprint", required=True)
    ap.add_argument("--handoff", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--feedback", help="Optional external evidence; never trusted for acceptance")
    args = ap.parse_args(argv)
    try:
        result = deliver(args.blueprint, args.handoff, args.output, args.feedback)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("materialized") else 10
    except (ValueError, OSError, TypeError, KeyError, adapter.MaterializationError,
            adapter.PinIntegrityError) as exc:
        print(json.dumps({"status": "REJECTED_NO_AUTHORITY",
                          "reason": type(exc).__name__,
                          "execution": False, "runtime_admission": False}))
        return 12


if __name__ == "__main__":
    sys.exit(main())
