"""Contract boundary tests for optional agent-capabilities reference handoff."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "consumer"))
import agent_capabilities_adapter as A

GOLDEN = HERE / "tests" / "fixtures" / "prompt-maker" / "golden-react-vite-supabase.json"


def fixture():
    bp = json.loads(GOLDEN.read_text(encoding="utf-8"))
    bp["product_surfaces"] = ["PUBLIC", "AUTHENTICATED"]
    bp["confirmed_requirements"] = [{"field": "design_references", "value": "RTL typography",
                                     "status": "CONFIRMED"}]
    raw = (json.dumps(bp, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    side = {
        "contract_id": A.CONTRACT, "schema_version": "1.0",
        "producer": {
            "product_id": "PROMPT_MAKER",
            "blueprint_schema_version": "1.1", "blueprint_sha256": digest,
            "project_name": bp["project_name"]},
        "authority": {
            "product": "PROMPT_MAKER", "materialization": "PROJECT_FACTORY",
            "agent_runtime": "AGENTIC", "authorization": "WORKSPACE",
            "runtime_admission": False, "execution_authorized": False},
        "ui_ux_design": {
            "status": "REFERENCE_REQUEST_ONLY", "agent": "UI_UX_DESIGNER",
            "required_review": True, "product_surfaces": bp["product_surfaces"],
            "target_platforms": bp["target_platforms"],
            "confirmed_design_references": ["RTL typography"],
            "output_claim": "NOT_GENERATED"},
        "skills_selection": {
            "status": "NOT_INVOKED", "capability": "skills.select.read_only",
            "runtime_admitted": False, "source_class": "SOVEREIGN_INTERNAL_PRIORITY",
            "request": {
                "task_id": "pmref_" + digest[:24],
                "description": "UI UX accessibility design review engineering reference",
                "scope": "engineering_reference", "requested_mode": "read_only_reference"},
            "selected_skills": []},
        "visual_qa_feedback": {
            "status": "NOT_RUN", "reviewed_by_agent": False,
            "findings": [], "evidence": [],
            "acceptance_authority": "WORKSPACE_NOT_DELEGATED"},
        "materialization": {
            "status": "FACTORY_CONSUMER_TO_DECIDE",
            "candidate_only": True, "production_ready": False}}
    return bp, raw, side


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.bp, self.raw, self.side = fixture()

    def test_reference_contract_valid(self):
        A.validate_handoff(self.bp, self.raw, self.side)

    def test_reject_false_agent_admission(self):
        s = copy.deepcopy(self.side)
        s["authority"]["runtime_admission"] = True
        with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_AGENT"):
            A.validate_handoff(self.bp, self.raw, s)

    def test_reject_false_skill_selection(self):
        s = copy.deepcopy(self.side)
        s["skills_selection"]["selected_skills"] = ["untrusted-agent"]
        with self.assertRaisesRegex(ValueError, "SKILLS_EXECUTION"):
            A.validate_handoff(self.bp, self.raw, s)

    def test_reject_mutating_skill_request(self):
        s = copy.deepcopy(self.side)
        s["skills_selection"]["request"]["requested_mode"] = "execute"
        with self.assertRaisesRegex(ValueError, "SKILLS_REQUEST"):
            A.validate_handoff(self.bp, self.raw, s)

    def test_reject_unverified_visual_qa_pass(self):
        s = copy.deepcopy(self.side)
        s["visual_qa_feedback"]["status"] = "PASS"
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_VISUAL"):
            A.validate_handoff(self.bp, self.raw, s)

    def test_reject_mismatched_blueprint_digest(self):
        s = copy.deepcopy(self.side)
        s["producer"]["blueprint_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "BLUEPRINT_IDENTITY"):
            A.validate_handoff(self.bp, self.raw, s)

    def test_reject_forged_design_context(self):
        s = copy.deepcopy(self.side)
        s["ui_ux_design"]["confirmed_design_references"].append("forged")
        with self.assertRaisesRegex(ValueError, "DESIGN_REFERENCE"):
            A.validate_handoff(self.bp, self.raw, s)

    def test_reject_unknown_contract_fields(self):
        s = copy.deepcopy(self.side)
        s["execution"] = True
        with self.assertRaisesRegex(ValueError, "INVALID_HANDOFF_KEYS"):
            A.validate_handoff(self.bp, self.raw, s)

    def test_unverified_external_qa_not_mistaken_for_approval(self):
        q = {"schema_version": "1.0", "status": "REPORT_AVAILABLE",
             "findings": ["Needs human review"],
             "evidence": [{"reference": "sha256-log", "sha256": "a" * 64}]}
        result = A.parse_feedback(q)
        self.assertEqual(result["status"], "UNVERIFIED_EXTERNAL_REPORT")
        self.assertEqual(result["acceptance_authority"], "NOT_DELEGATED")
        self.assertFalse(result["reviewed_by_agent"])

    def test_external_qa_requires_digest_evidence(self):
        q = {"schema_version": "1.0", "status": "REPORT_AVAILABLE",
             "findings": [], "evidence": [{"reference": "x", "sha256": "not-a-hash"}]}
        with self.assertRaisesRegex(ValueError, "INVALID_VISUAL_QA"):
            A.parse_feedback(q)

    def test_end_to_end_attaches_reference_separate_from_pinned_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bp = tmp / "bp.json"
            hand = tmp / "handoff.json"
            bp.write_bytes(self.raw)
            hand.write_text(json.dumps(self.side), encoding="utf-8")
            target = tmp / "generated"
            result = A.deliver(bp, hand, target)
            self.assertTrue(result["materialized"], result)
            self.assertEqual(result["agent_capabilities_status"], A.STATUS)
            self.assertFalse(result["execution"])
            self.assertFalse(result["runtime_admission"])
            self.assertFalse(result["production_ready"])
            doc = target / "docs" / "ai" / "AGENT_CAPABILITIES_REFERENCE_V1.json"
            prov = target / "docs" / "ai" / "AGENT_CAPABILITIES_REFERENCE_PROVENANCE_V1.json"
            self.assertEqual(hashlib.sha256(doc.read_bytes()).hexdigest(),
                             json.loads(prov.read_text(encoding="utf-8"))["reference_sha256"])
            self.assertTrue((target / "docs" / "ai" / "MATERIALIZATION_PROVENANCE.json").is_file())
            self.assertTrue((target / "docs" / "ai" / "BLUEPRINT_CONSUMER_SUBSET.json").is_file())

    def test_existing_directory_is_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bp, hand = tmp / "bp.json", tmp / "handoff.json"
            bp.write_bytes(self.raw)
            hand.write_text(json.dumps(self.side), encoding="utf-8")
            target = tmp / "already"
            target.mkdir()
            marker = target / "user.txt"
            marker.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "OUTPUT_ALREADY_EXISTS"):
                A.deliver(bp, hand, target)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
            self.assertEqual([x.name for x in target.iterdir()], ["user.txt"])

    def test_invalid_handoff_touches_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bp, hand = tmp / "bp.json", tmp / "handoff.json"
            bp.write_bytes(self.raw)
            bad = copy.deepcopy(self.side)
            bad["authority"]["execution_authorized"] = True
            hand.write_text(json.dumps(bad), encoding="utf-8")
            target = tmp / "output"
            with self.assertRaises(ValueError):
                A.deliver(bp, hand, target)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
