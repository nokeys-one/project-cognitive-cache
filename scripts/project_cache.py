#!/usr/bin/env python3
"""Maintain a token-cheap project fingerprint without interpreting source code."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
CACHE_RELATIVE = Path(".learn-by-building/cache")
DEFAULT_MANIFEST = CACHE_RELATIVE / "fingerprint.json"
IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".learn-by-building",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
}


class CacheSafetyError(Exception):
    """Raised when a requested cache path could escape or follow a symlink."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit(payload: dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2))
    raise SystemExit(exit_code)


def run_git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=check,
        encoding="utf-8",
        errors="surrogateescape",
        capture_output=True,
    )


def git_root(root: Path) -> Path | None:
    try:
        result = run_git(root, "rev-parse", "--show-toplevel", check=False)
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        mode = path.lstat().st_mode
        digest.update(f"mode:{mode:o}\0".encode())
        if stat.S_ISLNK(mode):
            digest.update(b"symlink\0")
            digest.update(os.readlink(path).encode("utf-8", "surrogateescape"))
        elif stat.S_ISDIR(mode):
            digest.update(b"directory\0")
            nested_root = git_root(path)
            if nested_root == path.resolve():
                nested = build_git_state(path.resolve())
                digest.update(
                    json.dumps(nested, sort_keys=True, separators=(",", ":")).encode()
                )
            else:
                for relative in iter_project_files(path):
                    digest.update(relative.as_posix().encode("utf-8", "surrogateescape"))
                    digest.update(b"\0")
                    digest.update(sha256_path(path / relative).encode())
        elif stat.S_ISREG(mode):
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        else:
            digest.update(f"special:{stat.S_IFMT(mode):o}\0".encode())
    except FileNotFoundError:
        return "__deleted__"
    return digest.hexdigest()


def ignored(relative: Path) -> bool:
    return any(part in IGNORED_DIRS for part in relative.parts)


def cache_ignored(relative: Path) -> bool:
    return relative.parts[:2] == (".learn-by-building", "cache")


def name_status_paths(output: str) -> set[str]:
    tokens = output.split("\0")
    paths: set[str] = set()
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if not status:
            continue
        if index >= len(tokens):
            break
        first = tokens[index]
        index += 1
        if first and not cache_ignored(Path(first)):
            paths.add(Path(first).as_posix())
        if status[0] in {"R", "C"} and index < len(tokens):
            second = tokens[index]
            index += 1
            if second and not cache_ignored(Path(second)):
                paths.add(Path(second).as_posix())
    return paths


def git_dirty_paths(root: Path) -> list[str]:
    commands = (
        ("diff", "--name-status", "-z", "--find-renames"),
        ("diff", "--cached", "--name-status", "-z", "--find-renames"),
    )
    paths: set[str] = set()
    for command in commands:
        result = run_git(root, *command)
        paths.update(name_status_paths(result.stdout))
    untracked = run_git(root, "ls-files", "--others", "--exclude-standard", "-z")
    for value in untracked.stdout.split("\0"):
        if value and not cache_ignored(Path(value)):
            paths.add(Path(value).as_posix())
    return sorted(paths)


def git_hidden_paths(root: Path) -> list[str]:
    """Return tracked paths whose index flags can hide working-tree changes."""
    result = run_git(root, "ls-files", "-v", "-z")
    paths: set[str] = set()
    for record in result.stdout.split("\0"):
        if len(record) < 3 or record[1] != " ":
            continue
        tag, value = record[0], record[2:]
        if (tag.islower() or tag == "S") and not cache_ignored(Path(value)):
            paths.add(Path(value).as_posix())
    return sorted(paths)


def build_git_state(root: Path) -> dict[str, Any]:
    head_result = run_git(root, "rev-parse", "--verify", "HEAD", check=False)
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    dirty = {
        rel: sha256_path(root / rel)
        for rel in git_dirty_paths(root)
    }
    hidden = {
        rel: sha256_path(root / rel)
        for rel in git_hidden_paths(root)
    }
    return {"mode": "git", "head": head, "dirty": dirty, "hidden": hidden}


def iter_project_files(root: Path):
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for dirname in sorted(dirs):
            path = current_path / dirname
            relative = path.relative_to(root)
            if ignored(relative):
                continue
            if path.is_symlink():
                yield relative
            else:
                kept_dirs.append(dirname)
        dirs[:] = kept_dirs
        for filename in sorted(files):
            path = current_path / filename
            rel = path.relative_to(root)
            if not ignored(rel):
                yield rel


def build_plain_state(root: Path) -> dict[str, Any]:
    files = {
        rel.as_posix(): sha256_path(root / rel)
        for rel in iter_project_files(root)
    }
    return {"mode": "plain", "files": files}


def build_state(root: Path) -> tuple[Path, dict[str, Any]]:
    root = root.resolve()
    repository = git_root(root)
    if repository is not None:
        root = repository
        return root, build_git_state(root)
    return root, build_plain_state(root)


def manifest_path(root: Path, raw: str | None) -> Path:
    if raw is None:
        candidate = root / DEFAULT_MANIFEST
    else:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = root / candidate
    candidate = Path(os.path.abspath(str(candidate)))
    cache = root / CACHE_RELATIVE
    try:
        candidate.relative_to(cache)
    except ValueError as error:
        raise CacheSafetyError("manifest must stay inside the project cache") from error
    return candidate


def ensure_cache_directory(root: Path, directory: Path) -> None:
    cache = root / CACHE_RELATIVE
    try:
        relative = directory.relative_to(root)
        directory.relative_to(cache)
    except ValueError as error:
        raise CacheSafetyError("cache directory escapes the project root") from error

    current = root
    for part in relative.parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            current.mkdir(mode=0o700)
            mode = current.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise CacheSafetyError(f"cache path component is not a real directory: {current}")
        if current == cache or cache in current.parents:
            os.chmod(current, 0o700)


def validate_cache_target(root: Path, path: Path, create_parent: bool) -> None:
    cache = root / CACHE_RELATIVE
    try:
        path.relative_to(cache)
    except ValueError as error:
        raise CacheSafetyError("cache file escapes the project cache") from error

    if create_parent:
        ensure_cache_directory(root, path.parent)
    else:
        current = root
        for part in path.parent.relative_to(root).parts:
            current = current / part
            try:
                mode = current.lstat().st_mode
            except FileNotFoundError:
                return
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                raise CacheSafetyError(f"cache path component is not a real directory: {current}")

    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise CacheSafetyError(f"cache target is not a regular file: {path}")


def write_json(root: Path, path: Path, payload: dict[str, Any]) -> None:
    validate_cache_target(root, path, create_parent=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        data = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        validate_cache_target(root, path, create_parent=False)
        os.replace(str(temporary), str(path))
        os.chmod(path, 0o600)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def command_capture(args: argparse.Namespace) -> None:
    root = canonical_root(Path(args.root))
    granted, _ = consent_status(root)
    if not granted:
        emit({
            "captured": False,
            "error": "consent_required",
            "message": "run init only after explicit user approval",
        }, 3)
    root, state = build_state(root)
    path = manifest_path(root, args.manifest)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "captured_at": utc_now(),
        "root": str(root),
        "state": state,
    }
    write_json(root, path, payload)
    emit({"captured": True, "manifest": str(path), "mode": state["mode"]})


def git_head_changes(
    root: Path, old: str | None, new: str | None
) -> tuple[list[str], bool]:
    if not old or not new or old == new:
        return [], True
    result = run_git(
        root,
        "diff",
        "--name-status",
        "-z",
        "--find-renames",
        f"{old}..{new}",
        check=False,
    )
    if result.returncode != 0:
        return [], False
    return sorted(name_status_paths(result.stdout)), True


def compare_states(root: Path, old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    if old.get("mode") != new.get("mode"):
        return {
            "state": "changed",
            "changed_paths": [],
            "reasons": ["project mode changed"],
            "requires_rebuild": True,
        }

    changed: set[str] = set()
    reasons: list[str] = []
    requires_rebuild = False
    if new["mode"] == "git":
        if old.get("head") != new.get("head"):
            reasons.append("HEAD changed")
            head_paths, diff_available = git_head_changes(
                root, old.get("head"), new.get("head")
            )
            changed.update(head_paths)
            if not diff_available:
                reasons.append("HEAD diff unavailable")
                requires_rebuild = True
        old_dirty = old.get("dirty", {})
        new_dirty = new.get("dirty", {})
        for path in set(old_dirty) | set(new_dirty):
            if old_dirty.get(path) != new_dirty.get(path):
                changed.add(path)
        if old_dirty != new_dirty:
            reasons.append("working tree changed")
        old_hidden = old.get("hidden", {})
        new_hidden = new.get("hidden", {})
        for path in set(old_hidden) | set(new_hidden):
            if old_hidden.get(path) != new_hidden.get(path):
                changed.add(path)
        if old_hidden != new_hidden:
            reasons.append("hidden index path changed")
    else:
        old_files = old.get("files", {})
        new_files = new.get("files", {})
        for path in set(old_files) | set(new_files):
            if old_files.get(path) != new_files.get(path):
                changed.add(path)
        if changed:
            reasons.append("file content changed")

    state = "changed" if reasons or changed else "fresh"
    return {
        "state": state,
        "changed_paths": sorted(changed),
        "reasons": reasons,
        "requires_rebuild": requires_rebuild or bool(reasons and not changed),
    }


def validate_manifest_state(state: dict[str, Any]) -> None:
    mode = state.get("mode")
    if mode == "git":
        head = state.get("head")
        dirty = state.get("dirty")
        hidden = state.get("hidden")
        if head is not None and not isinstance(head, str):
            raise ValueError("git state head must be a string or null")
        if not isinstance(dirty, dict):
            raise ValueError("git state dirty must be a JSON object")
        if not all(isinstance(key, str) and isinstance(value, str) for key, value in dirty.items()):
            raise ValueError("git state dirty entries must be string pairs")
        if not isinstance(hidden, dict):
            raise ValueError("git state hidden must be a JSON object")
        if not all(isinstance(key, str) and isinstance(value, str) for key, value in hidden.items()):
            raise ValueError("git state hidden entries must be string pairs")
    elif mode == "plain":
        files = state.get("files")
        if not isinstance(files, dict):
            raise ValueError("plain state files must be a JSON object")
        if not all(isinstance(key, str) and isinstance(value, str) for key, value in files.items()):
            raise ValueError("plain state file entries must be string pairs")
    else:
        raise ValueError("manifest state mode must be git or plain")


def command_status(args: argparse.Namespace) -> None:
    root, current = build_state(Path(args.root))
    path = manifest_path(root, args.manifest)
    validate_cache_target(root, path, create_parent=False)
    if not path.exists():
        emit({
            "state": "missing",
            "changed_paths": [],
            "reasons": ["fingerprint manifest missing"],
            "requires_rebuild": True,
        })
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(previous, dict):
            raise ValueError("manifest must be a JSON object")
        if previous.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported schema version")
        old_state = previous["state"]
        if not isinstance(old_state, dict):
            raise ValueError("manifest state must be a JSON object")
        validate_manifest_state(old_state)
        if previous.get("root") != str(root):
            raise ValueError("manifest belongs to a different project root")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        emit({
            "state": "invalid",
            "changed_paths": [],
            "reasons": [str(error)],
            "requires_rebuild": True,
        }, 2)
    result = compare_states(root, old_state, current)
    result.update({"mode": current["mode"], "manifest": str(path)})
    emit(result)


def local_exclude(root: Path) -> bool:
    repository = git_root(root)
    if repository is None:
        return False
    result = run_git(repository, "rev-parse", "--git-path", "info/exclude")
    exclude = Path(result.stdout.strip())
    if not exclude.is_absolute():
        exclude = repository / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    if exclude.is_symlink():
        raise CacheSafetyError("Git local exclude file must not be a symlink")
    rule = "/.learn-by-building/cache/"
    existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    lines = existing.splitlines()
    if rule not in lines:
        with exclude.open("a", encoding="utf-8") as handle:
            if existing and not existing.endswith("\n"):
                handle.write("\n")
            handle.write(rule + "\n")
    return True


def canonical_root(root: Path) -> Path:
    root = root.resolve()
    return git_root(root) or root


def tracked_consent(root: Path) -> bool:
    if git_root(root) is None:
        return False
    result = run_git(
        root,
        "ls-files",
        "--error-unmatch",
        "--",
        (CACHE_RELATIVE / "consent.json").as_posix(),
        check=False,
    )
    return result.returncode == 0


def consent_status(root: Path) -> tuple[bool, str]:
    path = root / CACHE_RELATIVE / "consent.json"
    if tracked_consent(root):
        return False, "tracked"
    try:
        validate_cache_target(root, path, create_parent=False)
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False, "missing"
    except CacheSafetyError:
        return False, "unsafe_cache_path"
    except (OSError, json.JSONDecodeError):
        return False, "invalid"
    if not isinstance(payload, dict) or payload.get("granted") is not True:
        return False, "invalid"
    if payload.get("schema_version") != SCHEMA_VERSION:
        return False, "schema_mismatch"
    if payload.get("root") != str(root):
        return False, "root_mismatch"
    return True, "granted"


def command_init(args: argparse.Namespace) -> None:
    root = canonical_root(Path(args.root))
    cache = root / CACHE_RELATIVE
    if tracked_consent(root):
        raise CacheSafetyError("tracked consent cannot be used as local approval")
    ensure_cache_directory(root, cache / "modules")
    excluded = local_exclude(root)
    consent = {
        "schema_version": SCHEMA_VERSION,
        "granted": True,
        "granted_at": utc_now(),
        "root": str(root),
        "scope": "local project cognitive cache",
    }
    write_json(root, cache / "consent.json", consent)
    emit({
        "initialized": True,
        "consent_recorded": True,
        "git_local_exclude": excluded,
        "cache": str(cache),
    })


def command_consent(args: argparse.Namespace) -> None:
    root = canonical_root(Path(args.root))
    path = root / CACHE_RELATIVE / "consent.json"
    granted, reason = consent_status(root)
    emit(
        {"granted": granted, "consent": str(path), "reason": reason},
        0 if granted else 1,
    )


def count_text(path: Path) -> tuple[int, int, int]:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    cjk = len(re.findall(r"[\u3400-\u9fff]", text))
    words = len(re.findall(r"[A-Za-z0-9_'-]+", text))
    return cjk, words, len(raw)


def command_validate(args: argparse.Namespace) -> None:
    root = canonical_root(Path(args.root))
    cache = root / CACHE_RELATIVE
    validate_cache_target(root, cache / "overview.md", create_parent=False)
    checks: list[tuple[Path, int, int, int]] = [
        (cache / "overview.md", 1800, 600, 7200)
    ]
    modules = cache / "modules"
    try:
        modules_mode = modules.lstat().st_mode
    except FileNotFoundError:
        modules_mode = None
    if modules_mode is not None and (stat.S_ISLNK(modules_mode) or not stat.S_ISDIR(modules_mode)):
        raise CacheSafetyError(f"cache path component is not a real directory: {modules}")
    if modules.exists():
        checks.extend(
            (path, 1200, 400, 4800) for path in sorted(modules.glob("*.md"))
        )
    violations: list[dict[str, Any]] = []
    for path, cjk_limit, word_limit, byte_limit in checks:
        validate_cache_target(root, path, create_parent=False)
        relative = path.relative_to(cache).as_posix()
        if not path.exists():
            violations.append({"path": relative, "reason": "missing"})
            continue
        try:
            cjk, words, utf8_bytes = count_text(path)
        except UnicodeDecodeError:
            violations.append({"path": relative, "reason": "not UTF-8 text"})
            continue
        if cjk > cjk_limit or words > word_limit:
            violations.append({
                "path": relative,
                "reason": "size limit exceeded",
                "cjk_characters": cjk,
                "cjk_limit": cjk_limit,
                "words": words,
                "word_limit": word_limit,
            })
        elif utf8_bytes > byte_limit:
            violations.append({
                "path": relative,
                "reason": "UTF-8 byte limit exceeded",
                "utf8_bytes": utf8_bytes,
                "byte_limit": byte_limit,
            })
    emit({"valid": not violations, "violations": violations}, 1 if violations else 0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create and compare project fingerprints without loading source into model context."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="record consent and initialize local cache")
    init.add_argument("--root", default=".")
    init.set_defaults(func=command_init)

    consent = subparsers.add_parser("consent", help="check recorded cache permission")
    consent.add_argument("--root", default=".")
    consent.set_defaults(func=command_consent)

    for name, function in (("capture", command_capture), ("status", command_status)):
        command = subparsers.add_parser(name)
        command.add_argument("--root", default=".")
        command.add_argument("--manifest")
        command.set_defaults(func=function)

    validate = subparsers.add_parser("validate", help="check cache layer size limits")
    validate.add_argument("--root", default=".")
    validate.set_defaults(func=command_validate)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except CacheSafetyError as error:
        emit({"error": "unsafe_cache_path", "message": str(error)}, 2)


if __name__ == "__main__":
    main()
