"""Exercise the public CLI against temporary, synthetic vaults."""

import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/para-second-brain/scripts/validate.sh"


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="para-vault-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for category in ("Inbox", "Projects", "Areas", "Resources", "Archive"):
            (self.root / category).mkdir()

    def note(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_check(self, *flags, expected=0):
        result = subprocess.run(["bash", str(SCRIPT), str(self.root), "--json", *flags], capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def codes(self, report):
        return {item["code"] for item in report["findings"]}

    def test_valid_single_note_project_in_portuguese_is_read_only(self):
        path = self.note("Projects/Entrega.md", "# Entrega\n- Status: ativo\n- Objetivo: publicar guia\n- [ ] Revisar texto\n")
        before = {p.relative_to(self.root): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(self.run_check()["counts"], {"error": 0, "warning": 0, "info": 0})
        after = {p.relative_to(self.root): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertTrue(path.exists())

    def test_folder_project_with_linked_tasks_does_not_require_agents(self):
        self.note("Projects/Release/README.md", '---\nstatus: active\ngoal: "Ship release"\n---\n[Tasks](Tasks.md)\n')
        self.note("Projects/Release/Tasks.md", "- [ ] Verify delivery\n")
        self.assertEqual(self.run_check()["findings"], [])

    def test_missing_category_is_structural_error(self):
        (self.root / "Areas").rmdir()
        self.assertIn("missing_category", self.codes(self.run_check("--structure", expected=1)))

    def test_missing_project_fields_are_warnings_not_structural_errors(self):
        self.note("Projects/Unclear.md", "# Goal\n\n## Tasks\n")
        codes = self.codes(self.run_check())
        self.assertTrue({"missing_goal", "missing_status", "missing_next_action"} <= codes)

    def test_old_active_project_is_not_declared_completed(self):
        path = self.note("Projects/Blocked.md", "Status: active\nGoal: ship\n- [ ] Unblock\n")
        old = time.time() - 46 * 86400
        os.utime(path, (old, old))
        codes = self.codes(self.run_check("--project-health", "--stale-days", "45"))
        self.assertIn("inactive_project", codes)
        self.assertNotIn("archive_candidate", codes)

    def test_closed_project_does_not_require_pending_action(self):
        self.note("Projects/Finished.md", "Status: concluído\nObjetivo: publicar\n- [x] Publicado\n")
        self.assertEqual(self.codes(self.run_check()), {"archive_candidate"})

    def test_links_resolve_spaces_wikilinks_and_skip_code(self):
        self.note("Resources/A note.md", "# A note\n")
        self.note("Inbox/Links.md", '[source](../Resources/A%20note.md#section)\n[[A note|alias]]\n[web](https://example.com)\n```markdown\n[bad](absent.md)\n```\n`[bad](absent.md)`\n')
        self.assertEqual(self.run_check("--links")["findings"], [])

    def test_link_outside_vault_is_not_followed(self):
        self.note("Inbox/Links.md", "[bad](../../outside.md)\n")
        self.assertIn("unresolved_link", self.codes(self.run_check("--links")))

    def test_symlinked_category_and_file_are_not_read(self):
        (self.root / "Areas").rmdir()
        (self.root / "Areas").symlink_to(self.root / "Resources", target_is_directory=True)
        (self.root / "Resources/Loop.md").symlink_to(self.root / "Resources/Loop.md")
        self.assertIn("missing_category", self.codes(self.run_check(expected=1)))

    def test_daily_age_is_based_on_filename(self):
        old = dt.date.today() - dt.timedelta(days=31)
        self.note(f"{old}.md", "# Old daily\n")
        self.assertIn("old_daily", self.codes(self.run_check("--daily")))

    def test_invalid_daily_date_is_a_warning(self):
        self.note("2026-02-30.md", "# Impossible\n")
        self.assertIn("invalid_daily_date", self.codes(self.run_check("--daily")))

    def test_structure_only_does_not_read_invalid_note(self):
        (self.root / "Inbox/Binary.md").write_bytes(b"\xff\xfe")
        self.assertEqual(self.run_check("--structure")["findings"], [])
        result = subprocess.run(["bash", str(SCRIPT), str(self.root)], capture_output=True)
        self.assertEqual(result.returncode, 2)

    def test_invalid_path_and_threshold_are_usage_errors(self):
        for arguments in ([str(self.root / "missing")], [str(self.root), "--stale-days", "0"]):
            result = subprocess.run(["bash", str(SCRIPT), *arguments], capture_output=True)
            self.assertEqual(result.returncode, 2)


class PackagingTests(unittest.TestCase):
    def test_skill_frontmatter_and_relative_references(self):
        skill = REPO / "skills/para-second-brain/SKILL.md"
        text = skill.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: para-second-brain\n"))
        description = next(line for line in text.splitlines() if line.startswith("description: "))
        self.assertLessEqual(len(description.removeprefix("description: ")), 1024)
        import re
        for document in skill.parent.rglob("*.md"):
            for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if "://" not in target:
                    self.assertTrue((document.parent / target.split("#", 1)[0]).is_file(), f"{document}: {target}")


if __name__ == "__main__":
    unittest.main()
