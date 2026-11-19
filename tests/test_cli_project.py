"""Multi-project: id minted on init, registry, --project resume, project link re-bind,
default via project use, list link-health, details, and a stable Windows-safe fingerprint."""

import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from viber.app import build_app
from viber.core import projects
from viber.data.store import load_census

runner = CliRunner()


@pytest.fixture(scope="module")
def app() -> Any:
    return build_app()


@pytest.fixture
def seed(tmp_path: Path, mini: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> Path:
    from viber.core import bootstrap

    path = tmp_path / "seed.json"
    path.write_text(json.dumps(mini), encoding="utf-8")
    monkeypatch.setattr(bootstrap, "load_seed", lambda: (load_census(path), path))
    return path


def call(app: Any, args: list[str]) -> Any:
    return runner.invoke(app, args)


def _init_project(tmp_path: Path, monkeypatch, name: str = "proj") -> str:
    project_dir = tmp_path / name
    (project_dir / ".viber" / ".data").mkdir(parents=True)
    monkeypatch.chdir(project_dir)
    assert runner.invoke(build_app(), ["init", "-nr"]).exit_code == 0
    return load_census(project_dir / ".viber" / ".data" / "viber.json").project_id


def test_init_mints_registers_and_banners(
    app: Any, seed: Path, tmp_path: Path, monkeypatch
) -> None:
    project_dir = tmp_path / "repo"
    (project_dir / ".viber" / ".data").mkdir(parents=True)
    monkeypatch.chdir(project_dir)
    r = call(app, ["init", "-nr"])
    assert r.exit_code == 0 and "PROJECT STARTED" in r.output and "viber --project" in r.output
    pid = load_census(project_dir / ".viber" / ".data" / "viber.json").project_id
    assert pid and f"id:    {pid}" in r.output
    rec = projects.lookup_project(os.environ, pid)
    assert rec and Path(rec["dir"]).resolve() == project_dir.resolve()


def test_project_resume_via_flag(app: Any, seed: Path, tmp_path: Path, monkeypatch) -> None:
    pid = _init_project(tmp_path, monkeypatch)
    (tmp_path / "elsewhere").mkdir()
    monkeypatch.chdir(tmp_path / "elsewhere")
    r = call(app, ["now", "--project", pid, "-f", "json"])
    assert r.exit_code == 0 and json.loads(r.output)["id"] == pid


def test_unknown_project_id_hints_link(
    app: Any, seed: Path, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    r = call(app, ["now", "--project", "deadbeef12"])
    assert r.exit_code == 2 and "viber project link" in r.output and "viber project list" in r.output


def test_link_rebinds_after_move(app: Any, seed: Path, tmp_path: Path, monkeypatch) -> None:
    old = tmp_path / "oldproj"
    (old / ".viber" / ".data").mkdir(parents=True)
    monkeypatch.chdir(old)
    assert call(app, ["init", "-nr"]).exit_code == 0
    pid = load_census(old / ".viber" / ".data" / "viber.json").project_id
    new = tmp_path / "newproj"
    new.mkdir()
    shutil.move(str(old / ".viber"), str(new / ".viber"))
    monkeypatch.chdir(tmp_path)
    assert json.loads(call(app, ["now", "--project", pid, "-f", "json"]).output)["present"] is False
    rows = json.loads(call(app, ["project", "list", "-f", "json"]).output)["rows"]
    assert any(row["link"] == "missing" for row in rows)
    link = call(app, ["project", "link", pid, "--to", str(new)])
    assert link.exit_code == 0 and "LINKED" in link.output
    assert json.loads(call(app, ["now", "--project", pid, "-f", "json"]).output)["present"] is True


def test_project_use_sets_default(app: Any, seed: Path, tmp_path: Path, monkeypatch) -> None:
    pid = _init_project(tmp_path, monkeypatch)
    assert call(app, ["project", "use", pid]).exit_code == 0
    (tmp_path / "other").mkdir()
    monkeypatch.chdir(tmp_path / "other")
    data = json.loads(call(app, ["now", "-f", "json"]).output)
    assert data["id"] == pid and data["source"] == "project"


def test_project_details_expands(app: Any, seed: Path, tmp_path: Path, monkeypatch) -> None:
    pid = _init_project(tmp_path, monkeypatch)
    r = call(app, ["project", "status", pid, "--details", "-f", "json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["id"] == pid
    assert data["present"] is True
    assert data["skills"] >= 1
    assert "recurring_pending" in data and "phase" in data and "last_action" in data


def test_project_flag_accepted_by_census_commands(
    app: Any, seed: Path, tmp_path: Path, monkeypatch
) -> None:
    pid = _init_project(tmp_path, monkeypatch)
    for cmd in (
        ["list"], ["stats"], ["deck"], ["patterns"], ["lint"], ["step", "Idea & Understanding"],
    ):
        r = call(app, cmd + ["--project", pid, "-f", "json"])
        assert "No such option: --project" not in r.output, cmd
        assert r.exit_code != 2, (cmd, r.output)  # accepted (lint may exit 1 on findings)


def test_fingerprint_is_path_stable(tmp_path: Path) -> None:
    d = tmp_path / "Some Project"
    d.mkdir()
    assert (
        projects.project_id(d)
        == projects.project_id(d.as_posix())
        == projects.project_id(Path(str(d) + "/"))
    )
    assert len(projects.project_id(d)) == 12


def test_git_boundary_stops_walkup(
    app: Any, seed: Path, tmp_path: Path, monkeypatch
) -> None:
    def make_git(d: Path, as_file: bool) -> None:
        if as_file:
            d.joinpath(".git").write_text("gitdir: ../main/.git/worktrees/x\n", encoding="utf-8")
        else:
            (d / ".git").mkdir(); (d / ".git" / "HEAD").write_text("ref: main\n", encoding="utf-8")

    main = tmp_path / "main"; (main / ".viber" / ".data").mkdir(parents=True); make_git(main, False)
    call(app, ["init", "-C", str(main / ".viber/.data/viber.json"), "-nr"])
    pid_main = load_census(main / ".viber/.data/viber.json").project_id

    # a nested git worktree inside main: .git FILE but no own data yet
    feat = main / "worktrees" / "feat"; (feat / "src" / "deep").mkdir(parents=True); make_git(feat, True)
    monkeypatch.chdir(feat / "src" / "deep")
    data = json.loads(call(app, ["now", "-f", "json"]).output)
    assert data["id"] != pid_main and data["present"] is False  # the .git boundary stops the climb

    # once it has its own data, deep inside resolves ITSELF, not main
    (feat / ".viber" / ".data").mkdir(parents=True)
    call(app, ["init", "-C", str(feat / ".viber/.data/viber.json"), "-nr"])
    pid_feat = load_census(feat / ".viber/.data/viber.json").project_id
    assert pid_feat != pid_main
    monkeypatch.chdir(feat / "src" / "deep")
    assert json.loads(call(app, ["now", "-f", "json"]).output)["id"] == pid_feat


def test_all_commands_target_the_same_project(
    app: Any, seed: Path, tmp_path: Path, monkeypatch
) -> None:
    pid = _init_project(tmp_path, monkeypatch, "solo")
    monkeypatch.chdir(tmp_path)  # unrelated cwd — only --project identifies the project
    census = tmp_path / "solo" / ".viber/.data/viber.json"
    call(app, ["use", "idea-md", "--project", pid])
    # reads agree they are the same project, and the write landed in ITS census, not cwd's
    for cmd in (["now"], ["status"], ["next"], ["list"]):
        assert call(app, cmd + ["--project", pid, "-f", "json"]).exit_code == 0
    assert json.loads(call(app, ["stats", "idea-md", "--project", pid, "-f", "json"]).output)["rows"]["count"] == 1
    assert (tmp_path / "solo" / ".viber/.data/telemetry.db").is_file()  # telemetry landed in solo's dir
    assert not (tmp_path / ".viber").exists()  # the unrelated cwd stayed clean


def test_committed_census_cannot_drift_the_id(
    app: Any, seed: Path, tmp_path: Path, monkeypatch
) -> None:
    from viber.core import projects
    from viber.data.store import save_census

    pid = _init_project(tmp_path, monkeypatch, "proj")
    census = tmp_path / "proj" / ".viber/.data/viber.json"
    # simulate checking out a branch whose committed census carries a foreign id
    data = load_census(census)
    data.project_id = "FOREIGNid0000"
    save_census(census, data)
    monkeypatch.chdir(tmp_path / "proj")
    resolved = json.loads(call(app, ["now", "-f", "json"]).output)
    assert resolved["id"] == projects.id_for_census(census)  # location wins
    assert resolved["id"] != "FOREIGNid0000"
    assert resolved.get("stored_id_differs") == "FOREIGNid0000"
    # resume by the real id still works regardless of the stored field
    assert json.loads(call(app, ["next", "--project", pid, "-f", "json"]).output).get("step")


def test_nested_project_innermost_wins(
    app: Any, seed: Path, tmp_path: Path, monkeypatch
) -> None:
    pidOuter = _init_project(tmp_path, monkeypatch, "outer")
    inner = tmp_path / "outer" / "inner"
    (inner / ".viber" / ".data").mkdir(parents=True)
    call(app, ["init", "-C", str(inner / ".viber/.data/viber.json"), "-nr"])
    pidInner = load_census(inner / ".viber/.data/viber.json").project_id
    deep = inner / "src"; deep.mkdir(parents=True)
    monkeypatch.chdir(deep)  # inside inner's subtree -> innermost wins
    assert json.loads(call(app, ["now", "-f", "json"]).output)["id"] == pidInner
    plain = tmp_path / "outer" / "plain"; plain.mkdir(parents=True)
    monkeypatch.chdir(plain)  # under outer only -> outer
    assert json.loads(call(app, ["now", "-f", "json"]).output)["id"] == pidOuter


def test_resolves_enclosing_project_from_deep_subfolder(
    app: Any, seed: Path, tmp_path: Path, monkeypatch
) -> None:
    pidA = _init_project(tmp_path, monkeypatch, "A")
    pidB = _init_project(tmp_path, monkeypatch, "B")
    call(app, ["project", "use", pidB])  # saved default = B
    deep = tmp_path / "A" / "src" / "nested" / "deeper"
    deep.mkdir(parents=True)
    monkeypatch.chdir(deep)
    # walking up from the deep folder finds A; A (local) beats the saved default B
    data = json.loads(call(app, ["now", "-f", "json"]).output)
    assert data["id"] == pidA and data["source"] == "cwd"
    # an explicit --project still overrides the enclosing-folder discovery
    forced = json.loads(call(app, ["now", "--project", pidB, "-f", "json"]).output)
    assert forced["id"] == pidB and forced["source"] == "project"


def test_two_projects_are_isolated(
    app: Any, seed: Path, tmp_path: Path, monkeypatch
) -> None:
    pidA = _init_project(tmp_path, monkeypatch, "A")
    pidB = _init_project(tmp_path, monkeypatch, "B")
    call(app, ["set", "idea-md", "recurring", "true", "--project", pidA])
    call(app, ["use", "idea-md", "--project", pidA])
    call(app, ["outcome", "idea-md", "skip", "--project", pidA, "later"])
    call(app, ["set", ".", "phase", "IP", "--project", pidA])
    a = json.loads(call(app, ["next", "--project", pidA, "-f", "json"]).output)
    b = json.loads(call(app, ["next", "--project", pidB, "-f", "json"]).output)
    assert a["step"] == "Implementation" and any(x["skill"] == "idea-md" for x in a["revisit"])
    assert b["step"] == "Idea & Understanding" and b["revisit"] == []
    assert json.loads(call(app, ["stats", "--project", pidB, "-f", "json"]).output)["present"] is False


def test_saved_default_does_not_override_the_local_project(
    app: Any, seed: Path, tmp_path: Path, monkeypatch
) -> None:
    pidA = _init_project(tmp_path, monkeypatch, "A")
    pidB = _init_project(tmp_path, monkeypatch, "B")
    assert call(app, ["project", "use", pidA]).exit_code == 0  # default = A
    a_dir = tmp_path / "A"
    monkeypatch.chdir(a_dir)  # standing inside A
    assert json.loads(call(app, ["now", "-f", "json"]).output)["id"] == pidA
    b_dir = tmp_path / "B"
    monkeypatch.chdir(b_dir)  # standing inside B -> local beats the saved default
    data = json.loads(call(app, ["now", "-f", "json"]).output)
    assert data["id"] == pidB and data["source"] == "cwd"
    # explicit --project still overrides the folder you are in
    assert json.loads(call(app, ["next", "--project", pidA, "-f", "json"]).output)["step"] == (
        "Idea & Understanding"
    )


def test_link_overlap_warns(app: Any, seed: Path, tmp_path: Path, monkeypatch) -> None:
    pidA = _init_project(tmp_path, monkeypatch, "A")
    pidB = _init_project(tmp_path, monkeypatch, "B")
    r = call(app, ["project", "link", pidA, "--to", str(tmp_path / "B"), "-nr"])
    assert "overlap" in r.output.lower() and pidB in r.output
