#!/usr/bin/env python3
"""Batch B tests: Prompt Maker consumer adapter + legacy generate.sh regression. Stdlib only.
Run:  python3 -m unittest discover -s tests -v     (from the repo root)"""
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from consumer import adapter as A  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "prompt-maker"
# Values dictated by the accepted Prompt Maker Batch A report (independently re-verified there).
PM_COMMIT = "f659f92d34449f093de05be6cc52a7f6c5221c84"
PM_GOLDEN = "df3e618dc3ef9abaf3878b3a6cda81e3c55f01b78182fc49ffe4b79160aa222e"
PM_MAPPING = "74b71c798e1f73b41450cf8a5b93e2e7c1183f70bb7146f4f78377332c0fa5ec"
PM_SCHEMA = "c0ce0b73a1e8e80697216445c10e654fc2f0ea5cbc32cdc8617c6ebb681ca9cb"
BASE_FACTORY_HEAD = "9aeff39e960503691d642d64f2eddb60fa10dd3e"


def fx(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def golden():
    return fx("golden-react-vite-supabase.json")


def tree_snapshot(d):
    d = Path(d)
    return {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.rglob("*")) if p.is_file()}


class PinTests(unittest.TestCase):
    def test_pin_values_match_accepted_producer_report(self):
        pin = A.load_pin(verify=True)
        self.assertEqual(pin["producer_repository"], "firasfanon/Palwakf_Prompt_Maker")
        self.assertEqual(pin["producer_contract_commit"], PM_COMMIT)
        self.assertEqual(pin["project_blueprint_schema"], "1.1")
        self.assertEqual(pin["consumer_subset_version"], 1)
        self.assertEqual(pin["fixture_version"], 1)
        self.assertEqual(pin["golden_fixture_sha256"], PM_GOLDEN)
        self.assertEqual(pin["profile_mapping_sha256"], PM_MAPPING)
        self.assertEqual(pin["consumer_schema_sha256"], PM_SCHEMA)

    def test_every_vendored_file_hash_readback(self):
        pin = A.load_pin(verify=False)
        for rel, want in pin["files"].items():
            self.assertEqual(A.sha256_lf((ROOT / rel).read_bytes()), want, rel)
        man = json.loads((FIX / "manifest.json").read_text(encoding="utf-8"))
        for f in man["fixtures"]:
            self.assertEqual(A.sha256_lf((FIX / f["file"]).read_bytes()), f["sha256"], f["fixture_id"])
        self.assertEqual(man["producer_base_head"], pin["producer_base_head"])

    def test_tampered_pin_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            saved = A.PIN_DIR, A.FACTORY_DIR
            try:
                shutil.copytree(ROOT / "consumer", Path(t) / "consumer")
                shutil.copytree(ROOT / "tests" / "fixtures", Path(t) / "tests" / "fixtures")
                (Path(t) / "consumer" / "pin" / "profile-mapping-v1.json").write_text("{}", encoding="utf-8")
                A.PIN_DIR, A.FACTORY_DIR = Path(t) / "consumer" / "pin", Path(t)
                with self.assertRaises(A.PinIntegrityError):
                    A.evaluate(golden())
            finally:
                A.PIN_DIR, A.FACTORY_DIR = saved

    def test_schema_required_equals_adapter_fields(self):
        schema = json.loads((ROOT / "consumer/pin/consumer-subset-v1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(schema["required"]), sorted(A.SUBSET_FIELDS))

    def test_mapped_profiles_exist_and_generic_is_unreachable(self):
        m = A.load_mapping()
        for p in m["profiles"]:
            self.assertTrue((ROOT / "profiles" / p["profile_id"] / "scaffold").is_dir(), p["profile_id"])
            self.assertIn(p["profile_id"], A.PROFILE_PROPERTIES)
        self.assertNotIn("generic", [p["profile_id"] for p in m["profiles"]])
        for s in ("generic", "Generic", " GENERIC "):
            self.assertEqual(A.resolve_profile(s, m)[0], "UNSUPPORTED")


class OutcomeTests(unittest.TestCase):
    def test_fixture_matrix_matches_manifest(self):
        man = json.loads((FIX / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(man["fixtures"]), 5)
        for f in man["fixtures"]:
            r = A.evaluate(fx(f["file"]))
            self.assertEqual(r["outcome"], f["expected_result"], f["fixture_id"])
            self.assertEqual(r.get("profile"), f["expected_profile"], f["fixture_id"])
        self.assertEqual(sorted(f["expected_result"] for f in man["fixtures"]), sorted(A.OUTCOMES))

    def test_golden_ready_react_vite_supabase(self):
        r = A.evaluate(golden())
        self.assertEqual((r["outcome"], r["classification"], r["profile"]), ("MATERIALIZATION_READY", "SUPPORTED_EXACT", "react-vite-supabase"))

    def test_alias_is_documented_alias_only(self):
        g = golden(); g["technology_decision"]["stack"] = "React + Vite + Supabase"
        r = A.evaluate(g)
        self.assertEqual((r["outcome"], r["classification"]), ("MATERIALIZATION_READY", "SUPPORTED_ALIAS"))
        for bad in ("react vite supabase", "React with Supabase", "react-vite", "react-vite-supabase-v2", "Vue + Supabase", ""):
            g["technology_decision"]["stack"] = bad
            self.assertIn(A.evaluate(g)["outcome"], ("BLOCKED_UNSUPPORTED_TECHNOLOGY_PROFILE", "INVALID_BLUEPRINT"), bad)

    def test_non_confirmed_statuses_block_even_with_a_stack(self):
        for st in ("REQUIRES_DECISION", "DEFERRED_WITH_GATE", "NOT_APPLICABLE_WITH_RATIONALE"):
            g = golden(); g["technology_decision"]["status"] = st
            self.assertEqual(A.evaluate(g)["outcome"], "BLOCKED_REQUIRES_TECHNOLOGY_DECISION", st)

    def test_no_stack_inference_from_profiles_architecture_or_text(self):
        n = fx("negative-requires-technology-decision.json")
        n["project_goal"] = "تطبيق React Vite Supabase"
        n["project_profiles"].append({"profile_id": "REACT_VITE_SUPABASE"})
        n["architecture_target"]["pattern"] = "react-vite-supabase"
        n["technology_decision"]["profile_hint"] = "react-vite-supabase"
        r = A.evaluate(n)
        self.assertEqual(r["outcome"], "BLOCKED_REQUIRES_TECHNOLOGY_DECISION")
        self.assertNotIn("profile", r)

    def test_confirmed_requires_user_confirmed_source(self):
        for src in ("INFERRED_DEFAULT", "PROFILE", "RULE", None):
            g = golden(); g["technology_decision"]["source_type"] = src
            self.assertEqual(A.evaluate(g)["outcome"], "INVALID_BLUEPRINT", str(src))

    def test_unsupported_confirmed_is_not_invalid_and_never_substituted(self):
        r = A.evaluate(fx("negative-unsupported-technology-profile.json"))
        self.assertEqual(r["outcome"], "BLOCKED_UNSUPPORTED_TECHNOLOGY_PROFILE")
        self.assertNotIn("profile", r)

    def test_schema_checked_first_and_missing_is_invalid(self):
        self.assertEqual(A.evaluate({"schema_version": "3.0", "x": 1})["outcome"], "UNSUPPORTED_BLUEPRINT_SCHEMA")
        for v in ("1.0", "1.2", "1.1.0", "2.0"):
            g = golden(); g["schema_version"] = v
            self.assertEqual(A.evaluate(g)["outcome"], "UNSUPPORTED_BLUEPRINT_SCHEMA", v)
        g = golden(); del g["schema_version"]
        self.assertEqual(A.evaluate(g)["outcome"], "INVALID_BLUEPRINT")
        g = golden(); g["schema_version"] = 1.1
        self.assertEqual(A.evaluate(g)["outcome"], "INVALID_BLUEPRINT")
        for bad in (None, [], "x", 5):
            self.assertEqual(A.evaluate(bad)["outcome"], "INVALID_BLUEPRINT")

    def test_every_required_field_removal_is_invalid(self):
        for f in A.SUBSET_FIELDS:
            if f == "schema_version":
                continue
            g = golden(); del g[f]
            self.assertEqual(A.evaluate(g)["outcome"], "INVALID_BLUEPRINT", f)
        g = golden(); g["target_platforms"] = []
        self.assertEqual(A.evaluate(g)["outcome"], "MATERIALIZATION_READY")

    def test_underscore_and_unknown_fields_ignored_never_required(self):
        g = golden(); g["_internal"] = {"x": 1}; g["future_field"] = [1]
        self.assertEqual(A.evaluate(g)["outcome"], "MATERIALIZATION_READY")
        self.assertNotIn("_internal", A.extract_subset(g))
        self.assertEqual(json.dumps(A.extract_subset(g)), json.dumps(A.extract_subset(golden())))

    def test_full_blueprint_input_is_accepted_via_projection(self):
        g = golden(); g["requirements_by_domain"] = {"a": 1}; g["_all_applicability"] = {}
        self.assertEqual(A.evaluate(g)["outcome"], "MATERIALIZATION_READY")

    def test_control_characters_in_name_are_invalid(self):
        g = golden(); g["project_name"] = "a\nb"
        self.assertEqual(A.evaluate(g)["outcome"], "INVALID_BLUEPRINT")

    def test_blocked_outcomes_touch_no_filesystem(self):
        for name in ("negative-requires-technology-decision.json", "negative-unsupported-technology-profile.json",
                     "negative-unsupported-blueprint-schema.json", "negative-invalid-consumer-subset.json"):
            with tempfile.TemporaryDirectory() as t:
                out = Path(t) / "never"
                r = A.materialize(fx(name), out)
                self.assertFalse(r["materialized"], name)
                self.assertFalse(out.exists(), name + " must not even create the output dir")


class MaterializationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "proj"

    def tearDown(self):
        self.tmp.cleanup()

    def run_golden(self, **kw):
        return A.materialize(golden(), self.out, project_date="2026-10-08", **kw)

    def test_real_scaffold_and_docs_generated_and_validated(self):
        r = self.run_golden()
        self.assertEqual(r["status"], "MATERIALIZED_AND_VALIDATED", r["validation"])
        for rel in ("package.json", "index.html", "vite.config.ts", "tsconfig.json", "src/App.tsx", "src/main.tsx",
                    "src/lib/supabase.ts", ".env.example", ".gitignore", "docs/ai/00_MASTER_CONTEXT.md",
                    "docs/ai/TECH_STACK.md", A.PROVENANCE_FILE, A.SUBSET_FILE):
            self.assertTrue((self.out / rel).is_file(), rel)
        self.assertEqual(sum(1 for f in (self.out / "docs/ai").glob("*.md")), 23)
        pkg = json.loads((self.out / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["name"], "golden-consumer-project")
        self.assertIn("react", pkg["dependencies"])
        self.assertIn("@supabase/supabase-js", pkg["dependencies"])
        # profile overlay really replaced the generic doc
        self.assertIn("Vite", (self.out / "docs/ai/TECH_STACK.md").read_text(encoding="utf-8"))
        # nothing from the other profile
        self.assertFalse((self.out / "pubspec.yaml").exists())

    def test_no_unresolved_template_tokens_in_output(self):
        self.run_golden()
        for p in self.out.rglob("*"):
            if p.is_file() and p.suffix in (".md", ".json", ".html", ".tsx", ".ts"):
                self.assertNotRegex(p.read_text(encoding="utf-8"), r"\{\{[A-Z_]+\}\}", p.name)

    def test_provenance_pins_producer_and_hashes_files(self):
        self.run_golden()
        prov = json.loads((self.out / A.PROVENANCE_FILE).read_text(encoding="utf-8"))
        self.assertEqual(prov["producer_contract_commit"], PM_COMMIT)
        self.assertEqual(prov["profile_mapping_sha256"], PM_MAPPING)
        self.assertEqual(prov["consumer_schema_sha256"], PM_SCHEMA)
        self.assertEqual(prov["profile"], "react-vite-supabase")
        self.assertEqual(prov["blueprint_subset_sha256"], A.sha256_lf((self.out / A.SUBSET_FILE).read_bytes()))
        for rel, h in prov["files"].items():
            self.assertEqual(A.sha256_lf((self.out / rel).read_bytes()), h, rel)
        self.assertIn("NOT execution authority", prov["scope_note"])
        self.assertEqual(json.loads((self.out / A.SUBSET_FILE).read_text(encoding="utf-8")), A.extract_subset(golden()))

    def test_deterministic_for_same_input_and_date(self):
        self.run_golden()
        other = Path(self.tmp.name) / "proj2"
        A.materialize(golden(), other, project_date="2026-10-08")
        a, b = tree_snapshot(self.out), tree_snapshot(other)
        self.assertEqual(a, b)

    def test_idempotent_second_run_creates_nothing(self):
        self.run_golden()
        before = tree_snapshot(self.out)
        r2 = self.run_golden()
        self.assertEqual(r2["created"], [])
        self.assertEqual(tree_snapshot(self.out), before)
        self.assertGreater(len(r2["skipped_existing"]), 40)

    def test_no_clobber_preserves_existing_user_files(self):
        self.out.mkdir(parents=True)
        (self.out / "package.json").write_text('{"name":"mine"}', encoding="utf-8")
        (self.out / "docs/ai").mkdir(parents=True)
        (self.out / "docs/ai/PRD.md").write_text("MY PRD", encoding="utf-8")
        r = self.run_golden()
        self.assertEqual((self.out / "package.json").read_text(encoding="utf-8"), '{"name":"mine"}')
        self.assertEqual((self.out / "docs/ai/PRD.md").read_text(encoding="utf-8"), "MY PRD")
        self.assertIn("package.json", r["skipped_existing"])
        self.assertIn("docs/ai/PRD.md", r["skipped_existing"])
        self.assertTrue((self.out / "index.html").is_file())

    def test_no_clobber_does_not_follow_symlinks(self):
        self.out.mkdir(parents=True)
        victim = Path(self.tmp.name) / "victim.txt"
        victim.write_text("SAFE", encoding="utf-8")
        os.symlink(victim, self.out / "package.json")
        self.run_golden()
        self.assertEqual(victim.read_text(encoding="utf-8"), "SAFE")

    def test_refuses_to_write_inside_factory_tree(self):
        with self.assertRaises(A.MaterializationError):
            A.materialize(golden(), ROOT / "_should_not_exist")
        self.assertFalse((ROOT / "_should_not_exist").exists())

    def test_hostile_project_name_is_escaped_not_injected(self):
        g = golden()
        g["project_name"] = '</title><script>alert(1)</script>"{{PROJECT_OWNER}}'
        g["project_goal"] = 'x"; evil: {{PROJECT_STATUS}}'
        r = A.materialize(g, self.out, project_date="2026-10-08")
        self.assertEqual(r["status"], "MATERIALIZED_AND_VALIDATED", r["validation"])
        html_ = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>alert", html_)
        self.assertIn("&lt;/title&gt;", html_)
        tsx = (self.out / "src/App.tsx").read_text(encoding="utf-8")
        self.assertNotIn("<script>", tsx)
        self.assertIn("\\u003c/title>", tsx)
        # single-pass substitution: a token inside user input is NOT expanded
        self.assertIn("{{PROJECT_OWNER}}", (self.out / "README.md").read_text(encoding="utf-8") + (self.out / "docs/ai/00_MASTER_CONTEXT.md").read_text(encoding="utf-8"))

    def test_flutter_profile_materializes_only_via_confirmed_exact_or_alias(self):
        g = golden(); g["technology_decision"]["stack"] = "Flutter + Supabase"
        r = A.materialize(g, self.out, project_date="2026-10-08")
        self.assertEqual((r["outcome"], r["classification"], r["profile"]), ("MATERIALIZATION_READY", "SUPPORTED_ALIAS", "flutter-supabase"))
        self.assertEqual(r["status"], "MATERIALIZED_AND_VALIDATED", r["validation"])
        self.assertTrue((self.out / "pubspec.yaml").is_file())
        self.assertFalse((self.out / "package.json").exists())
        self.assertIn("class GoldenConsumerProjectApp", (self.out / "lib/app/app.dart").read_text(encoding="utf-8"))

    def test_dart_injection_is_escaped(self):
        g = golden(); g["technology_decision"]["stack"] = "flutter-supabase"
        g["project_name"] = "O'Brien $x \\ app"
        A.materialize(g, self.out, project_date="2026-10-08")
        dart = (self.out / "lib/app/app.dart").read_text(encoding="utf-8")
        self.assertIn("O\\'Brien \\$x \\\\ app", dart)

    def test_secret_residue_clean_on_generated_output(self):
        self.run_golden()
        for p in self.out.rglob("*"):
            if p.is_file():
                self.assertEqual(A.scan_secrets(p.name, p.read_text(encoding="utf-8", errors="ignore")), [], str(p))
        env = (self.out / ".env.example").read_text(encoding="utf-8")
        self.assertNotRegex(env, r"eyJ[A-Za-z0-9_-]{15,}")

    def test_secret_scanner_detects_planted_secrets(self):
        for s in ("-----BEGIN RSA PRIVATE KEY-----", "AKIAABCDEFGHIJKLMNOP",
                  "eyJhbGciOiJIUzI1NiIsInR5cCI6.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.abcdefghij1234",
                  "ghp_" + "a" * 36, 'service_role = "' + "x" * 30 + '"'):
            self.assertTrue(A.scan_secrets("f", s), s)

    def test_templates_only_use_known_tokens(self):
        known = set(A.substitute.build_tokens({}).keys())
        for prof in ("generic", "react-vite-supabase", "flutter-supabase"):
            for p in (ROOT / "profiles" / prof).rglob("*"):
                if p.is_file():
                    try:
                        txt = p.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        continue
                    for tok in re.findall(r"\{\{([A-Z_]+)\}\}", txt):
                        self.assertIn(tok, known, "%s uses unknown token %s" % (p, tok))

    def test_factory_source_tree_unchanged_by_materialization(self):
        before = subprocess.run(["git", "status", "--porcelain", "--", "profiles", "PROJECTS_REGISTRY.md", "VERSION"],
                                cwd=ROOT, capture_output=True, text=True).stdout
        self.run_golden()
        after = subprocess.run(["git", "status", "--porcelain", "--", "profiles", "PROJECTS_REGISTRY.md", "VERSION"],
                               cwd=ROOT, capture_output=True, text=True).stdout
        self.assertEqual(before, after)

    @unittest.skipUnless(shutil.which("tsc"), "tsc not installed")
    def test_generated_typescript_has_no_syntax_errors(self):
        """PARTIAL evidence only: syntax (TS1xxx) diagnostics. Module-resolution errors are expected
        without `npm install` and are NOT counted; this is not a build."""
        self.run_golden()
        srcs = [str(p) for p in (self.out / "src").rglob("*") if p.suffix in (".ts", ".tsx")] + [str(self.out / "vite.config.ts")]
        r = subprocess.run(["tsc", "--noEmit", "--jsx", "preserve", "--skipLibCheck", "--target", "ES2020",
                            "--moduleResolution", "bundler", "--module", "ESNext"] + srcs,
                           capture_output=True, text=True, cwd=self.out)
        syntax = [l for l in r.stdout.splitlines() if re.search(r"error TS1\d{3}:", l)]
        self.assertEqual(syntax, [], "\n".join(syntax))


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-I", str(ROOT / "consumer" / "adapter.py")] + list(args),
                              capture_output=True, text=True)

    def test_exit_codes_per_outcome(self):
        want = {"golden-react-vite-supabase.json": 0, "negative-requires-technology-decision.json": 10,
                "negative-unsupported-technology-profile.json": 11, "negative-invalid-consumer-subset.json": 12,
                "negative-unsupported-blueprint-schema.json": 13}
        for f, code in want.items():
            r = self.run_cli("evaluate", "--blueprint", str(FIX / f))
            self.assertEqual(r.returncode, code, f + r.stderr)

    def test_unreadable_blueprint_is_invalid(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as t:
            t.write("not json")
        r = self.run_cli("evaluate", "--blueprint", t.name)
        os.unlink(t.name)
        self.assertEqual(r.returncode, 12)

    def test_cli_materialize_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_cli("materialize", "--blueprint", str(FIX / "golden-react-vite-supabase.json"), "--output", d + "/p", "--date", "2026-10-08")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(json.loads(r.stdout)["status"], "MATERIALIZED_AND_VALIDATED")
            r = self.run_cli("materialize", "--blueprint", str(FIX / "negative-requires-technology-decision.json"), "--output", d + "/q")
            self.assertEqual(r.returncode, 10)
            self.assertFalse(Path(d + "/q").exists())


class LegacyGenerateRegressionTests(unittest.TestCase):
    """The interactive generate.sh path must be byte-for-byte equivalent to the pre-Batch-B baseline
    (substitute.py was refactored to expose build_tokens)."""

    ANSWERS = "اختبار قديم\nlegacy-demo\nweb\nتطوير\nالمالك\nهدف تجريبي\n3\nn\ny\n{out}\n"

    def run_legacy(self, factory_dir, out):
        return subprocess.run(["bash", str(factory_dir / "generate.sh")], input=self.ANSWERS.format(out=out),
                              capture_output=True, text=True, timeout=60)

    def test_legacy_output_identical_to_base_commit(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            base = t / "base"
            base.mkdir()
            tar = subprocess.run(["git", "archive", BASE_FACTORY_HEAD], cwd=ROOT, capture_output=True)
            if tar.returncode != 0:
                self.skipTest("base commit not available in this (shallow) clone")
            subprocess.run(["tar", "-x", "-C", str(base)], input=tar.stdout, check=True)
            cur = t / "cur"
            shutil.copytree(ROOT, cur, ignore=lambda d, names: [n for n in names if n in (".git", "__pycache__") or (Path(d) == ROOT and n == "tests")])
            rb = self.run_legacy(base, t / "out_base")
            rc = self.run_legacy(cur, t / "out_cur")
            self.assertEqual(rb.returncode, 0, rb.stderr)
            self.assertEqual(rc.returncode, 0, rc.stderr)
            self.assertEqual(tree_snapshot(t / "out_base"), tree_snapshot(t / "out_cur"))
            self.assertGreater(len(tree_snapshot(t / "out_cur")), 40)


if __name__ == "__main__":
    unittest.main()
