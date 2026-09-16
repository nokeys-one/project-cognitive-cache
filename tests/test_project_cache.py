import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "project_cache.py"


def run_tool(*args, cwd=None, expect=0, env=None, timeout=10):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
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
    def test_init_rejects_symlinked_cache_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "project"
            outside = base / "outside"
            root.mkdir()
            outside.mkdir()
            (root / ".learn-by-building").symlink_to(outside, target_is_directory=True)

            result = run_tool("init", "--root", root, expect=2)

            self.assertEqual("unsafe_cache_path", result["error"])
            self.assertFalse((outside / "cache/consent.json").exists())

    def test_capture_does_not_follow_predictable_temporary_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "project"
            root.mkdir()
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            run_tool("init", "--root", root)
            victim = base / "victim.txt"
            victim.write_text("do not overwrite\n", encoding="utf-8")
            predictable = root / ".learn-by-building/cache/fingerprint.json.tmp"
            predictable.symlink_to(victim)

            result = run_tool("capture", "--root", root)

            self.assertTrue(result["captured"])
            self.assertEqual("do not overwrite\n", victim.read_text(encoding="utf-8"))

    def test_capture_rejects_manifest_outside_project_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "project"
            root.mkdir()
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            run_tool("init", "--root", root)
            outside = base / "fingerprint.json"

            result = run_tool(
                "capture", "--root", root, "--manifest", outside, expect=2
            )

            self.assertEqual("unsafe_cache_path", result["error"])
            self.assertFalse(outside.exists())

    def test_status_rejects_symlinked_cache_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "project"
            outside = base / "outside"
            root.mkdir()
            (outside / "cache").mkdir(parents=True)
            (outside / "cache/fingerprint.json").write_text("{}", encoding="utf-8")
            (root / ".learn-by-building").symlink_to(outside, target_is_directory=True)

            result = run_tool("status", "--root", root, expect=2)

            self.assertEqual("unsafe_cache_path", result["error"])

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
            self.assertEqual(str(root.resolve()), consent["root"])
            exclude = (root / ".git/info/exclude").read_text("utf-8")
            self.assertIn("/.learn-by-building/cache/", exclude)
            self.assertFalse((root / ".gitignore").exists())
            after = run_tool("consent", "--root", root)
            self.assertTrue(after["granted"])

    def test_tracked_consent_file_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "-q")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "Test User")
            run_tool("init", "--root", root)
            git(root, "add", "-f", ".learn-by-building/cache/consent.json")
            git(root, "commit", "-qm", "forge consent")

            result = run_tool("consent", "--root", root, expect=1)

            self.assertFalse(result["granted"])
            self.assertEqual("tracked", result["reason"])

    def test_consent_bound_to_another_root_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_tool("init", "--root", root)
            consent_path = root / ".learn-by-building/cache/consent.json"
            consent = json.loads(consent_path.read_text(encoding="utf-8"))
            consent["root"] = str(root / "elsewhere")
            consent_path.write_text(json.dumps(consent), encoding="utf-8")

            result = run_tool("consent", "--root", root, expect=1)

            self.assertFalse(result["granted"])
            self.assertEqual("root_mismatch", result["reason"])

    @unittest.skipIf(os.name == "nt", "POSIX permission bits required")
    def test_cache_directories_and_machine_files_are_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            run_tool("init", "--root", root)
            run_tool("capture", "--root", root)
            cache = root / ".learn-by-building/cache"

            self.assertEqual(0o700, stat.S_IMODE(cache.stat().st_mode))
            self.assertEqual(0o700, stat.S_IMODE((cache / "modules").stat().st_mode))
            self.assertEqual(0o600, stat.S_IMODE((cache / "consent.json").stat().st_mode))
            self.assertEqual(0o600, stat.S_IMODE((cache / "fingerprint.json").stat().st_mode))

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

    def test_plain_source_in_generic_build_directories_is_not_ignored(self):
        for directory in ("vendor", "target", "build", "dist"):
            with self.subTest(directory=directory), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / directory / "core.py"
                source.parent.mkdir()
                source.write_text("VERSION = 1\n", encoding="utf-8")
                run_tool("init", "--root", root)
                run_tool("capture", "--root", root)

                source.write_text("VERSION = 2\n", encoding="utf-8")
                changed = run_tool("status", "--root", root)

                self.assertEqual("changed", changed["state"])
                self.assertEqual([f"{directory}/core.py"], changed["changed_paths"])

    def test_assume_unchanged_file_content_is_fingerprinted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "-q")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "Test User")
            (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            git(root, "add", "app.py")
            git(root, "commit", "-qm", "initial")
            run_tool("init", "--root", root)
            run_tool("capture", "--root", root)
            git(root, "update-index", "--assume-unchanged", "app.py")

            (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
            changed = run_tool("status", "--root", root)

            self.assertEqual("changed", changed["state"])
            self.assertEqual(["app.py"], changed["changed_paths"])

    def test_skip_worktree_file_content_is_fingerprinted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "-q")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "Test User")
            (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            git(root, "add", "app.py")
            git(root, "commit", "-qm", "initial")
            run_tool("init", "--root", root)
            run_tool("capture", "--root", root)
            git(root, "update-index", "--skip-worktree", "app.py")

            (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
            changed = run_tool("status", "--root", root)

            self.assertEqual("changed", changed["state"])
            self.assertEqual(["app.py"], changed["changed_paths"])

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

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO support required")
    def test_plain_snapshot_does_not_open_fifo_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("pass\n", encoding="utf-8")
            os.mkfifo(root / "events.pipe")
            run_tool("init", "--root", root)

            captured = run_tool("capture", "--root", root, timeout=3)

            self.assertTrue(captured["captured"])

    @unittest.skipIf(os.name == "nt", "surrogateescape filename test is POSIX-only")
    def test_non_utf8_filename_is_serialized_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_path = os.fsencode(root) + b"/module_\xff.py"
            descriptor = os.open(raw_path, os.O_WRONLY | os.O_CREAT, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(b"pass\n")
            run_tool("init", "--root", root)

            captured = run_tool("capture", "--root", root)
            fresh = run_tool("status", "--root", root)

            self.assertTrue(captured["captured"])
            self.assertEqual("fresh", fresh["state"])

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

    def test_validate_enforces_utf8_byte_limit_for_other_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / ".learn-by-building/cache"
            modules = cache / "modules"
            modules.mkdir(parents=True)
            (cache / "overview.md").write_text("あ" * 3000, encoding="utf-8")
            (modules / "auth.md").write_text("ok\n", encoding="utf-8")

            invalid = run_tool("validate", "--root", root, expect=1)

            self.assertFalse(invalid["valid"])
            self.assertEqual("overview.md", invalid["violations"][0]["path"])
            self.assertEqual("UTF-8 byte limit exceeded", invalid["violations"][0]["reason"])

    def test_validate_resolves_git_subdirectory_to_repository_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "-q")
            cache = root / ".learn-by-building/cache"
            modules = cache / "modules"
            modules.mkdir(parents=True)
            (cache / "overview.md").write_text("small\n", encoding="utf-8")
            (modules / "auth.md").write_text("small\n", encoding="utf-8")
            subdirectory = root / "src"
            subdirectory.mkdir()

            valid = run_tool("validate", "--root", subdirectory)

            self.assertTrue(valid["valid"])

    def test_validate_rejects_symlinked_cache_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "project"
            outside = base / "outside"
            root.mkdir()
            (outside / "cache/modules").mkdir(parents=True)
            (outside / "cache/overview.md").write_text("small\n", encoding="utf-8")
            (outside / "cache/modules/auth.md").write_text(
                "small\n", encoding="utf-8"
            )
            (root / ".learn-by-building").symlink_to(outside, target_is_directory=True)

            result = run_tool("validate", "--root", root, expect=2)

            self.assertEqual("unsafe_cache_path", result["error"])

    def test_failed_head_diff_requires_rebuild_even_with_dirty_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "-q")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "Test User")
            (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            git(root, "add", "app.py")
            git(root, "commit", "-qm", "initial")
            run_tool("init", "--root", root)
            run_tool("capture", "--root", root)
            manifest_path = root / ".learn-by-building/cache/fingerprint.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["state"]["head"] = "0" * 40
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            (root / "dirty.py").write_text("DIRTY = True\n", encoding="utf-8")

            changed = run_tool("status", "--root", root)

            self.assertEqual("changed", changed["state"])
            self.assertTrue(changed["requires_rebuild"])
            self.assertIn("HEAD diff unavailable", changed["reasons"])


if __name__ == "__main__":
    unittest.main()
