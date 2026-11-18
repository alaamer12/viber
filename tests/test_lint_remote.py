"""Deck remote checks (--remote): fake-git matrix over every outcome, plus the
symref parser. Live network behavior is verified manually via `viber lint --remote`."""

import json
from pathlib import Path
from typing import Any

from viber.core.lint import _parse_symref_head, check_deck_remotes
from viber.data.store import load_census
from viber.models.domain import Severity

SHA_LOCAL = "a" * 40
SHA_UP = "b" * 40
LS_OK = f"ref: refs/heads/main\tHEAD\n{SHA_UP}\tHEAD\n"


def fake_git(
    *, is_repo: bool = True, ls: tuple[int, str] | None = (0, LS_OK), head: str = SHA_LOCAL
) -> Any:
    def run(args: list[str], cwd: str) -> tuple[int, str]:
        if args[:2] == ["rev-parse", "--git-dir"]:
            return (0, ".git") if is_repo else (128, "")
        if args[0] == "ls-remote":
            return ls if ls is not None else (128, "")
        if args[:2] == ["rev-parse", "HEAD"]:
            return 0, head
        return 0, ""

    return run


def census_with_decks(
    tmp_path: Path, mini: dict[str, Any], decks: dict[str, dict[str, Any]]
) -> Any:
    data = json.loads(json.dumps(mini))
    for name, patch in decks.items():
        data["decks"][name].update(patch)
    p = tmp_path / "viber.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return load_census(p)


def test_symref_parser_reads_branch_and_sha() -> None:
    assert _parse_symref_head(LS_OK) == ("main", SHA_UP)
    assert _parse_symref_head("ref: refs/heads/main\tHEAD\n") is None
    assert _parse_symref_head("") is None


def test_no_remote_means_no_calls(tmp_path: Path, mini: dict[str, Any]) -> None:
    census = census_with_decks(
        tmp_path, mini, {"author": {"remote": None}, "project": {"remote": None}}
    )
    calls: list[list[str]] = []

    def spy(args: list[str], cwd: str) -> tuple[int, str]:
        calls.append(args)
        return 0, ""

    assert check_deck_remotes(census, tmp_path, spy) == []
    assert calls == []


def test_pointer_registry_warns_no_clone(tmp_path: Path, mini: dict[str, Any]) -> None:
    census = census_with_decks(
        tmp_path, mini, {"author": {"remote": "https://x/repo", "registry": ".viber/registry.md"}}
    )
    findings = check_deck_remotes(census, tmp_path, fake_git())
    assert [f.check for f in findings] == ["remote-no-clone"]
    assert findings[0].severity is Severity.WARNING


def test_non_repo_directory_warns(tmp_path: Path, mini: dict[str, Any]) -> None:
    reg = tmp_path / "clone"
    reg.mkdir()
    census = census_with_decks(
        tmp_path, mini, {"author": {"remote": "https://x/repo", "registry": str(reg)}}
    )
    findings = check_deck_remotes(census, tmp_path, fake_git(is_repo=False))
    assert [f.check for f in findings] == ["remote-no-clone"]


def test_offline_is_unreachable_not_error(tmp_path: Path, mini: dict[str, Any]) -> None:
    reg = tmp_path / "clone"
    reg.mkdir()
    census = census_with_decks(
        tmp_path, mini, {"author": {"remote": "https://x/repo", "registry": str(reg)}}
    )
    findings = check_deck_remotes(census, tmp_path, fake_git(ls=None))
    assert [f.check for f in findings] == ["remote-unreachable"]


def test_equal_head_is_silent(tmp_path: Path, mini: dict[str, Any]) -> None:
    reg = tmp_path / "clone"
    reg.mkdir()
    census = census_with_decks(
        tmp_path, mini, {"author": {"remote": "https://x/repo", "registry": str(reg)}}
    )
    findings = check_deck_remotes(census, tmp_path, fake_git(head=SHA_UP))
    assert findings == []


def test_differing_head_names_both_shas_and_the_fix(
    tmp_path: Path, mini: dict[str, Any]
) -> None:
    reg = tmp_path / "clone"
    reg.mkdir()
    census = census_with_decks(
        tmp_path, mini, {"author": {"remote": "https://x/repo", "registry": str(reg)}}
    )
    findings = check_deck_remotes(census, tmp_path, fake_git())
    assert [f.check for f in findings] == ["remote-differs"]
    detail = findings[0].detail
    assert SHA_LOCAL[:8] in detail and SHA_UP[:8] in detail
    assert "git pull" in detail and "viber refresh --all" in detail
