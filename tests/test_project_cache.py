import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "project_cache.py"


def run_tool(*args, cwd=None, expect=0, env=None):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )
    if completed.returncode != expect:
        raise AssertionError(
            f"expected exit {expect}, got {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return json.loads(completed.stdout) if completed.stdout.strip() else None


def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True, capture_output=True
    ).stdout.strip()


class ProjectCacheTests(unittest.TestCase):
    def test_capture_refuses_to_write_without_recorded_consent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            manifest = root / ".learn-by-building/cache/fingerprint.json"
            result = run_tool(
                "capture", "--root", root, "--manifest", manifest, expect=3
            )
            self.assertEqual("consent_required", result["error"])
            self.assertFalse(manifest.exists())

    def test_git_clean_snapshot_is_fresh_then_head_change_lists_changed_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "-q")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "Test User")
            (root / "app.py").write_text("print('v1')\n", encoding="utf-8")
            git(root, "add", "app.py")
            git(root, "commit", "-qm", "initial")
            manifest = root / ".learn-by-building/cache/fingerprint.json"

            run_tool("init", "--root", root)
            run_tool("capture", "--root", root, "--manifest", manifest)
            fresh = run_tool("status", "--root", root, "--manifest", manifest)
            self.assertEqual("fresh", fresh["state"])

            (root / "app.py").write_text("print('v2')\n", encoding="utf-8")
            git(root, "add", "app.py")
            git(root, "commit", "-qm", "change app")
            changed = run_tool("status", "--root", root, "--manifest", manifest)
            self.assertEqual("changed", changed["state"])
            self.assertEqual(["app.py"], changed["changed_paths"])

    def test_git_dirty_file_content_change_is_detected_without_path_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "-q")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "Test User")
            (root / "auth.py").write_text("MODE = 'base'\n", encoding="utf-8")
            git(root, "add", "auth.py")
            git(root, "commit", "-qm", "initial")
            (root / "auth.py").write_text("MODE = 'dirty-one'\n", encoding="utf-8")
            manifest = root / ".learn-by-building/cache/fingerprint.json"
            run_tool("init", "--root", root)
            run_tool("capture", "--root", root, "--manifest", manifest)

            (root / "auth.py").write_text("MODE = 'dirty-two'\n", encoding="utf-8")
            changed = run_tool("status", "--root", root, "--manifest", manifest)
            self.assertEqual("changed", changed["state"])
            self.assertEqual(["auth.py"], changed["changed_paths"])

    def test_non_git_snapshot_detects_add_modify_and_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "keep.txt").write_text("before\n", encoding="utf-8")
            (root / "delete.txt").write_text("remove me\n", encoding="utf-8")
            manifest = root / ".learn-by-building/cache/fingerprint.json"
            run_tool("init", "--root", root)
            run_tool("capture", "--root", root, "--manifest", manifest)

            (root / "keep.txt").write_text("after\n", encoding="utf-8")
            (root / "delete.txt").unlink()
            (root / "added.txt").write_text("new\n", encoding="utf-8")
            changed = run_tool("status", "--root", root, "--manifest", manifest)
            self.assertEqual("changed", changed["state"])
            self.assertEqual(
                ["added.txt", "delete.txt", "keep.txt"], changed["changed_paths"]
            )

    def test_init_records_consent_and_uses_git_local_exclude(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "-q")
            before = run_tool("consent", "--root", root, expect=1)
            self.assertFalse(before["granted"])
            result = run_tool("init", "--root", root)
            self.assertTrue(result["consent_recorded"])
            consent = json.loads(
                (root / ".learn-by-building/cache/consent.json").read_text("utf-8")
            )
            self.assertTrue(consent["granted"])
            exclude = (root / ".git/info/exclude").read_text("utf-8")
            self.assertIn("/.learn-by-building/cache/", exclude)
            self.assertFalse((root / ".gitignore").exists())
            after = run_tool("consent", "--root", root)
            self.assertTrue(after["granted"])

    def test_cache_files_and_heavy_directories_do_not_invalidate_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src/main.py").write_text("pass\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules/pkg.js").write_text("old\n", encoding="utf-8")
            manifest = root / ".learn-by-building/cache/fingerprint.json"
            run_tool("init", "--root", root)
            run_tool("capture", "--root", root, "--manifest", manifest)

            (root / "node_modules/pkg.js").write_text("new\n", encoding="utf-8")
            (root / ".learn-by-building/cache/overview.md").write_text(
                "updated summary\n", encoding="utf-8"
            )
            fresh = run_tool("status", "--root", root, "--manifest", manifest)
            self.assertEqual("fresh", fresh["state"])

    def test_git_tracked_files_are_not_excluded_by_generic_directory_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "-q")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "Test User")
            (root / "vendor").mkdir()
            (root / "vendor/core.py").write_text("VERSION = 1\n", encoding="utf-8")
            git(root, "add", "vendor/core.py")
            git(root, "commit", "-qm", "track vendor source")
            manifest = root / ".learn-by-building/cache/fingerprint.json"
            run_tool("init", "--root", root)
            run_tool("capture", "--root", root, "--manifest", manifest)

            (root / "vendor/core.py").write_text("VERSION = 2\n", encoding="utf-8")
            changed = run_tool("status", "--root", root, "--manifest", manifest)
            self.assertEqual("changed", changed["state"])
            self.assertEqual(["vendor/core.py"], changed["changed_paths"])

    def test_git_submodule_change_returns_changed_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sub = base / "sub"
            root = base / "root"
            sub.mkdir()
            root.mkdir()
            for repo in (sub, root):
                git(repo, "init", "-q")
                git(repo, "config", "user.email", "test@example.com")
                git(repo, "config", "user.name", "Test User")
            (sub / "lib.py").write_text("VALUE = 1\n", encoding="utf-8")
            git(sub, "add", "lib.py")
            git(sub, "commit", "-qm", "initial library")
            git(root, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(sub), "deps/lib")
            git(root, "commit", "-qam", "add submodule")
            manifest = root / ".learn-by-building/cache/fingerprint.json"
            run_tool("init", "--root", root)
            run_tool("capture", "--root", root, "--manifest", manifest)

            (root / "deps/lib/lib.py").write_text("VALUE = 2\n", encoding="utf-8")
            changed = run_tool("status", "--root", root, "--manifest", manifest)
            self.assertEqual("changed", changed["state"])
            self.assertEqual(["deps/lib"], changed["changed_paths"])

    def test_committed_rename_reports_old_and_new_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "-q")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "Test User")
            (root / "old.py").write_text("VALUE = 1\n", encoding="utf-8")
            git(root, "add", "old.py")
            git(root, "commit", "-qm", "initial")
            manifest = root / ".learn-by-building/cache/fingerprint.json"
            run_tool("init", "--root", root)
            run_tool("capture", "--root", root, "--manifest", manifest)

            git(root, "mv", "old.py", "new.py")
            git(root, "commit", "-qm", "rename module")
            changed = run_tool("status", "--root", root, "--manifest", manifest)
            self.assertEqual(["new.py", "old.py"], changed["changed_paths"])

    def test_malformed_manifest_returns_invalid_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            manifest = root / ".learn-by-building/cache/fingerprint.json"
            run_tool("init", "--root", root)
            manifest.write_text(
                json.dumps({"schema_version": 1, "state": []}), encoding="utf-8"
            )
            result = run_tool(
                "status", "--root", root, "--manifest", manifest, expect=2
            )
            self.assertEqual("invalid", result["state"])

    def test_malformed_nested_manifest_fields_return_invalid_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            manifest = root / ".learn-by-building/cache/fingerprint.json"
            run_tool("init", "--root", root)
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "root": str(root.resolve()),
                        "state": {"mode": "plain", "files": []},
                    }
                ),
                encoding="utf-8",
            )
            result = run_tool(
                "status", "--root", root, "--manifest", manifest, expect=2
            )
            self.assertEqual("invalid", result["state"])

    def test_manifest_from_another_project_root_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            first = base / "first"
            second = base / "second"
            first.mkdir()
            second.mkdir()
            (first / "app.py").write_text("pass\n", encoding="utf-8")
            (second / "app.py").write_text("pass\n", encoding="utf-8")
            first_manifest = first / ".learn-by-building/cache/fingerprint.json"
            second_manifest = second / ".learn-by-building/cache/fingerprint.json"
            run_tool("init", "--root", first)
            run_tool("capture", "--root", first, "--manifest", first_manifest)
            run_tool("init", "--root", second)
            second_manifest.write_text(
                first_manifest.read_text(encoding="utf-8"), encoding="utf-8"
            )

            result = run_tool(
                "status", "--root", second, "--manifest", second_manifest, expect=2
            )
            self.assertEqual("invalid", result["state"])
            self.assertTrue(result["requires_rebuild"])

    def test_non_git_directory_symlink_target_change_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "one").mkdir()
            (root / "two").mkdir()
            (root / "linked").symlink_to("one", target_is_directory=True)
            manifest = root / ".learn-by-building/cache/fingerprint.json"
            run_tool("init", "--root", root)
            run_tool("capture", "--root", root, "--manifest", manifest)

            (root / "linked").unlink()
            (root / "linked").symlink_to("two", target_is_directory=True)
            changed = run_tool("status", "--root", root, "--manifest", manifest)
            self.assertEqual("changed", changed["state"])
            self.assertEqual(["linked"], changed["changed_paths"])

    def test_non_git_mode_works_when_git_executable_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            clean_env = os.environ.copy()
            clean_env["PATH"] = ""
            result = run_tool(
                "consent", "--root", root, expect=1, env=clean_env
            )
            self.assertFalse(result["granted"])
            run_tool("init", "--root", root, env=clean_env)
            captured = run_tool("capture", "--root", root, env=clean_env)
            self.assertEqual("plain", captured["mode"])

    def test_validate_enforces_layer_size_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / ".learn-by-building/cache"
            modules = cache / "modules"
            modules.mkdir(parents=True)
            (cache / "overview.md").write_text("简" * 1801, encoding="utf-8")
            (modules / "auth.md").write_text("ok\n", encoding="utf-8")

            invalid = run_tool("validate", "--root", root, expect=1)
            self.assertFalse(invalid["valid"])
            self.assertEqual("overview.md", invalid["violations"][0]["path"])


if __name__ == "__main__":
    unittest.main()
