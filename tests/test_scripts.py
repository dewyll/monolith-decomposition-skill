"""End-to-end and unit tests for the skill's scripts. Run: python3 -m unittest -v"""
import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "plugins" / "monolith-decomposition" / "skills" / "decompose" / "scripts"
EXAMPLE = REPO / "examples" / "tiny-monolith"
sys.path.insert(0, str(SCRIPTS))

from common import glob_to_regex  # noqa: E402


def run(script, *args, check=True):
    proc = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise AssertionError(f"{script} failed ({proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
    return proc


def write(root: Path, files: dict):
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")


def edges_of(ws: Path):
    data = json.loads((ws / "04-dependencies" / "edges.json").read_text())
    return {(e["from"], e["to"]) for e in data["edges"]}


class GlobTest(unittest.TestCase):
    def test_double_star(self):
        rx = glob_to_regex("**/node_modules/**")
        self.assertTrue(rx.match("node_modules/a.js"))
        self.assertTrue(rx.match("web/node_modules/a/b.js"))
        self.assertFalse(rx.match("src/modules/a.js"))

    def test_single_star_stays_in_segment(self):
        rx = glob_to_regex("src/*.ts")
        self.assertTrue(rx.match("src/a.ts"))
        self.assertFalse(rx.match("src/x/a.ts"))


class TinyMonolithPipeline(unittest.TestCase):
    """Runs every phase on examples/tiny-monolith in a temp copy."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.proj = cls.tmp / "tiny"
        shutil.copytree(EXAMPLE, cls.proj, ignore=shutil.ignore_patterns("decomposition", "__pycache__"))
        cls.ws = cls.proj / "decomposition"
        run("init_workspace.py", cls.proj)
        run("size_components.py", "--workspace", cls.ws)
        run("extract_dependencies.py", "--workspace", cls.ws)
        run("analyze_dependencies.py", "--workspace", cls.ws)
        run("find_common_candidates.py", "--workspace", cls.ws)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def comps(self):
        return {c["id"]: c for c in json.loads((self.ws / "01-sizing" / "components.json").read_text())["components"]}

    def test_tests_are_excluded(self):
        self.assertNotIn("tests", self.comps())

    def test_root_with_code_detected(self):
        self.assertIn("root-with-code", self.comps()["shopco.orders"]["flags"])
        self.assertIn("shopco.orders.pricing", self.comps()["shopco.orders"]["children"])

    def test_large_component_flagged(self):
        self.assertIn("over-max", self.comps()["shopco.orders"]["flags"])

    def test_cycle_detected(self):
        deps = json.loads((self.ws / "04-dependencies" / "dependencies.json").read_text())
        members = [c["members"] for c in deps["cycles"]]
        self.assertIn(["shopco.inventory", "shopco.orders"], members)

    def test_expected_edges(self):
        e = edges_of(self.ws)
        for pair in [("shopco.orders", "shopco.orders.pricing"), ("shopco.reporting", "shopco.payments"),
                     ("shopco.payments", "shopco.notification"), ("shopco.inventory", "shopco.orders")]:
            self.assertIn(pair, e)

    def test_common_candidates(self):
        cands = json.loads((self.ws / "02-common-domain" / "candidates.json").read_text())
        ids = {c["component"] for c in cands["candidates"]}
        self.assertTrue({"shopco.notification", "shopco.orders.notification", "shopco.audit"} <= ids)
        self.assertEqual(cands["duplicate_groups"][0]["leaf"], "notification")

    def test_fitness_fails_on_known_problems(self):
        proc = run("check_fitness.py", "--workspace", self.ws, "--phase", "all", check=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("[FAIL] F3.1", proc.stdout)
        self.assertIn("[FAIL] F4.1", proc.stdout)

    def test_domains_and_services(self):
        domains = {"domains": [
            {"id": "ordering", "components": ["shopco", "shopco.orders", "shopco.orders.pricing",
                                              "shopco.orders.notification", "shopco.inventory"]},
            {"id": "customer", "components": ["shopco.customers"]},
            {"id": "payment", "components": ["shopco.payments"]},
            {"id": "reporting", "components": ["shopco.reporting"]},
            {"id": "shared", "components": ["shopco.audit", "shopco.notification"]},
        ]}
        (self.ws / "05-domains" / "domains.json").write_text(json.dumps(domains))
        run("analyze_dependencies.py", "--workspace", self.ws, "--domains", self.ws / "05-domains" / "domains.json")
        dc = json.loads((self.ws / "05-domains" / "domain-coupling.json").read_text())
        self.assertIn({"from": "reporting", "to": "payment", "weight": 1}, dc["edges"])
        self.assertEqual(dc["unmapped_components"], [])
        self.assertIn("[PASS] F5.1", run("check_fitness.py", "--workspace", self.ws, "--phase", "5",
                                         check=False).stdout)

        services = {"services": [
            {"id": "order-svc", "domains": ["ordering"], "interfaces": [
                {"to": "customer-svc"}, {"to": "shared-lib"}]},
            {"id": "customer-svc", "domains": ["customer"]},
            {"id": "payment-svc", "domains": ["payment"], "interfaces": [{"to": "shared-lib"}]},
            {"id": "reporting-svc", "domains": ["reporting"]},
            {"id": "shared-lib", "domains": ["shared"]},
        ]}
        (self.ws / "06-services" / "services.json").write_text(json.dumps(services))
        out = run("check_fitness.py", "--workspace", self.ws, "--phase", "6", check=False).stdout
        self.assertIn("[PASS] F6.1", out)
        self.assertIn("[FAIL] F6.2", out)   # reporting-svc calls others without declaring it
        self.assertIn("reporting-svc -> payment-svc", out)

    def test_forbidden_dependency_rule(self):
        cfg_path = self.ws / "config.json"
        cfg = json.loads(cfg_path.read_text())
        cfg["fitness"]["forbidden_dependencies"] = [
            {"from": "shopco.inventory", "to": "shopco.orders", "level": "component", "rfc": "0004"}]
        cfg_path.write_text(json.dumps(cfg))
        try:
            out = run("check_fitness.py", "--workspace", self.ws, "--phase", "5", check=False).stdout
            self.assertIn("[FAIL] F5.4", out)
        finally:
            cfg["fitness"]["forbidden_dependencies"] = []
            cfg_path.write_text(json.dumps(cfg))

    def test_rfc_and_state(self):
        path = Path(run("new_rfc.py", "--workspace", self.ws, "--title", "Sizing thresholds",
                        "--phase", "1").stdout.strip())
        self.assertTrue(path.name.startswith("0001-sizing-thresholds"))
        self.assertIn("RFC-0001: Sizing thresholds", path.read_text())
        run("new_rfc.py", "--workspace", self.ws, "--set-status", "1", "Accepted")
        self.assertIn("| Accepted |", (self.ws / "rfcs" / "index.md").read_text())

        run("state.py", "--workspace", self.ws, "start", "1")
        self.assertNotEqual(run("state.py", "--workspace", self.ws, "approve", "1", check=False).returncode, 0)
        run("state.py", "--workspace", self.ws, "review", "1", "--rfc", "0001")
        run("state.py", "--workspace", self.ws, "approve", "1")
        run("state.py", "--workspace", self.ws, "start", "2")
        run("state.py", "--workspace", self.ws, "review", "2")
        run("state.py", "--workspace", self.ws, "approve", "2")
        run("state.py", "--workspace", self.ws, "reopen", "1", "--reason", "test")
        state = json.loads((self.ws / "state.json").read_text())
        self.assertEqual(state["phases"]["2"]["status"], "stale")
        self.assertEqual(state["phases"]["1"]["iteration"], 2)


class ExtractorLanguages(unittest.TestCase):
    """The regex extractor resolves imports for several ecosystems."""

    def project(self, files, roots=None, aliases=None):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        write(tmp, files)
        run("init_workspace.py", tmp)
        ws = tmp / "decomposition"
        cfg = json.loads((ws / "config.json").read_text())
        if roots is not None:
            cfg["source_roots"] = roots
        if aliases:
            cfg["import_aliases"] = aliases
        (ws / "config.json").write_text(json.dumps(cfg))
        run("size_components.py", "--workspace", ws)
        run("extract_dependencies.py", "--workspace", ws)
        return ws

    def test_typescript_relative_and_alias(self):
        ws = self.project({
            "src/billing/invoice.ts": "import { Ship } from '../shipping/ship';\nimport x from '@/audit/log';\nimport _ from 'lodash';\n",
            "src/shipping/ship.ts": "export class Ship {}\n",
            "src/audit/log.ts": "export default 1;\n",
        }, aliases={"@/": "src/"})
        e = edges_of(ws)
        self.assertIn(("billing", "shipping"), e)
        self.assertIn(("billing", "audit"), e)

    def test_java_packages(self):
        ws = self.project({
            "src/main/java/com/acme/billing/Invoice.java":
                "package com.acme.billing;\nimport com.acme.shipping.Parcel;\nimport java.util.List;\n",
            "src/main/java/com/acme/shipping/Parcel.java": "package com.acme.shipping;\n",
        })
        self.assertIn(("com.acme.billing", "com.acme.shipping"), edges_of(ws))

    def test_go_module_prefix(self):
        ws = self.project({
            "go.mod": "module github.com/acme/shop\n\ngo 1.22\n",
            "internal/billing/billing.go":
                'package billing\n\nimport (\n\t"fmt"\n\ts "github.com/acme/shop/internal/shipping"\n)\n',
            "internal/shipping/shipping.go": "package shipping\n",
        })
        self.assertIn(("internal.billing", "internal.shipping"), edges_of(ws))

    def test_csharp_namespace_prefix(self):
        ws = self.project({
            "src/Billing/Invoice.cs": "using System;\nusing Acme.Shipping;\nnamespace Acme.Billing {}\n",
            "src/Shipping/Parcel.cs": "namespace Acme.Shipping {}\n",
        }, roots=[{"path": "src", "namespace_prefix": "Acme"}])
        self.assertIn(("Billing", "Shipping"), edges_of(ws))

    def test_php_composer_psr4(self):
        ws = self.project({
            "composer.json": json.dumps({"autoload": {"psr-4": {"Acme\\": "src/"}}}),
            "src/Billing/Invoice.php": "<?php\nnamespace Acme\\Billing;\nuse Acme\\Shipping\\Parcel;\n",
            "src/Shipping/Parcel.php": "<?php\nnamespace Acme\\Shipping;\n",
        })
        self.assertIn(("Billing", "Shipping"), edges_of(ws))

    def test_ruby_requires(self):
        ws = self.project({
            "lib/billing/invoice.rb": "require 'json'\nrequire 'shipping/parcel'\nrequire_relative '../audit/log'\n",
            "lib/shipping/parcel.rb": "class Parcel; end\n",
            "lib/audit/log.rb": "module Log; end\n",
        })
        e = edges_of(ws)
        self.assertIn(("billing", "shipping"), e)
        self.assertIn(("billing", "audit"), e)


class ConvertEdgesTest(unittest.TestCase):
    def test_namespace_pairs_and_explicit_components(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        write(tmp, {"packs/billing/a.rb": "x = 1\n", "packs/ordering/b.rb": "y = 2\n"})
        run("init_workspace.py", tmp)
        ws = tmp / "decomposition"
        cfg = json.loads((ws / "config.json").read_text())
        cfg["components"]["strategy"] = "explicit"
        cfg["components"]["explicit"] = [{"name": "billing", "paths": ["packs/billing/**"]},
                                         {"name": "ordering", "paths": ["packs/ordering/**"]}]
        (ws / "config.json").write_text(json.dumps(cfg))
        run("size_components.py", "--workspace", ws)
        comps = json.loads((ws / "01-sizing" / "components.json").read_text())["components"]
        self.assertEqual({c["path"] for c in comps}, {"packs/billing", "packs/ordering"})
        pairs = tmp / "pairs.tsv"
        pairs.write_text("packs/billing/a.rb\tpacks/ordering/b.rb\npacks/billing/a.rb\tgems/x.rb\n")
        run("convert_edges.py", pairs, "--workspace", ws, "--kind", "files", "--tool", "test")
        self.assertEqual(edges_of(ws), {("billing", "ordering")})


class SchemaTest(unittest.TestCase):
    """Validates generated artifacts against schemas/ when jsonschema is installed (CI installs it)."""

    def test_artifacts_match_schemas(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        schemas = SCRIPTS.parent / "schemas"
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        proj = tmp / "tiny"
        shutil.copytree(EXAMPLE, proj, ignore=shutil.ignore_patterns("decomposition", "__pycache__"))
        ws = proj / "decomposition"
        run("init_workspace.py", proj)
        run("size_components.py", "--workspace", ws)
        run("extract_dependencies.py", "--workspace", ws)
        for artifact, schema in [("config.json", "config"), ("state.json", "state"),
                                 ("01-sizing/components.json", "components"),
                                 ("04-dependencies/edges.json", "edges")]:
            with self.subTest(artifact=artifact):
                jsonschema.validate(json.loads((ws / artifact).read_text()),
                                    json.loads((schemas / f"{schema}.schema.json").read_text()))


if __name__ == "__main__":
    unittest.main()
