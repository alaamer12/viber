"""Limits: catalog consistency, write guards (transparent rejections), rolling
history with announced eviction, lint surfacing of already-written violations,
and the `viber fields` face of the catalog."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from viber.app import build_app
from viber.core.lint import run_limit_checks
from viber.data.store import load_census
from viber.models.limits import LIMITS, append_history, guard_chars

runner = CliRunner()


@pytest.fixture(scope="module")
def app() -> Any:
    return build_app()


def call(app: Any, args: list[str], census_file: Path) -> Any:
    return runner.invoke(app, args + ["-C", str(census_file)])


class TestCatalog:
    def test_every_limit_has_why_recovery_and_identity(self) -> None:
        for lim in LIMITS.values():
            assert lim.why and lim.recovery
            assert lim.identity.endswith(("MAX_CHARS", "MAX_ITEMS"))

    def test_message_carries_identity_cap_got_and_fix(self) -> None:
        msg = LIMITS["description"].message(9999)
        assert "DESCRIPTION_MAX_CHARS" in msg
        assert "4000 characters" in msg and "got 9999" in msg
        assert "Fix:" in msg and "viber refresh" in msg


class TestWriteGuards:
    def test_set_doing_over_cap_rejected_transparently(
        self, app: Any, census_file: Path
    ) -> None:
        r = call(app, ["set", "idea-md", "doing", '"x' + "y" * 2500 + '"'], census_file)
        assert r.exit_code == 2
        assert "DOING_MAX_CHARS" in r.output and "2000" in r.output

    def test_set_use_cases_list_over_cap_rejected(self, app: Any, census_file: Path) -> None:
        cases = json.dumps([f"case {i}" for i in range(40)])
        r = call(app, ["set", "idea-md", "use_cases", cases], census_file)
        assert r.exit_code == 2
        assert "USE_CASES_MAX_ITEMS" in r.output and "cap 30" not in r.output  # "30 records"
        assert "30 records" in r.output

    def test_guard_units_chars_and_items(self) -> None:
        with pytest.raises(ValueError) as exc:
            guard_chars("hint", "h" * 400)
        assert "HINT_MAX_CHARS" in str(exc.value)
        base = [{"date": "d", "event": str(i)} for i in range(99)]
        assert append_history(list(base), {"date": "d", "event": "new"}) == 0
        base.append({"date": "d", "event": "tenth"})
        assert append_history(list(base), {"date": "d", "event": "new"}) == 1


class TestRollingHistory:
    def test_log_past_cap_rolls_and_announces(self, app: Any, census_file: Path) -> None:
        data = json.loads(census_file.read_text(encoding="utf-8"))
        name = next(iter(data["skills"]))
        data["skills"][name]["history"] = [
            {"date": "2020-01-01", "event": f"old {i}"} for i in range(100)
        ]
        census_file.write_text(json.dumps(data), encoding="utf-8")
        r = call(app, ["log", name, "the new event"], census_file)
        assert r.exit_code == 0 and "rolled" in r.output
        after = json.loads(census_file.read_text(encoding="utf-8"))["skills"][name]["history"]
        assert len(after) == 100
        assert after[-1]["event"] == "the new event"
        assert not any(str(e["event"]).startswith("old 0") for e in after)


class TestLintSurfacesWrittenViolations:
    def test_over_cap_field_is_lint_error_not_load_crash(
        self, app: Any, census_file: Path
    ) -> None:
        data = json.loads(census_file.read_text(encoding="utf-8"))
        name = next(iter(data["skills"]))
        data["skills"][name]["description"] = "d" * 5000
        census_file.write_text(json.dumps(data), encoding="utf-8")
        census = load_census(census_file)  # readable — no lockout
        findings = run_limit_checks(census)
        assert any(
            f.check == "limit-violation" and "DESCRIPTION_MAX_CHARS" in f.detail for f in findings
        )
        r = call(app, ["lint"], census_file)
        assert r.exit_code == 1 and "DESCRIPTION_MAX_CHARS" in r.output


class TestFieldsCommand:
    def test_table_lists_every_field(self, app: Any, census_file: Path) -> None:
        r = call(app, ["fields", "-nr"], census_file)  # plain: no rich width-squash
        assert r.exit_code == 0
        for probe in ("fit.doing", "step.possible_skills", "relation.hint", "Meaning"):
            assert probe in r.output

    def test_json_machine_shape(self, app: Any, census_file: Path) -> None:
        r = call(app, ["fields", "-f", "json"], census_file)
        rows = json.loads(r.output)["fields"]
        assert any(row["field"] == "skill.history" and row["limit"] == "history" for row in rows)

    def test_single_field_is_fully_explained(self, app: Any, census_file: Path) -> None:
        r = call(app, ["fields", "fit.doing"], census_file)
        assert r.exit_code == 0
        for probe in ("DOING_MAX_CHARS", "2000", "written_by", "used_by", "viber set"):
            assert probe in r.output

    def test_unknown_field_says_so(self, app: Any, census_file: Path) -> None:
        r = call(app, ["fields", "nosuchfield"], census_file)
        assert r.exit_code == 1 and "viber fields" in r.output

    def test_every_schema_field_is_documented(self) -> None:
        from viber.models.fields_doc import FIELD_DOCS, FIELD_INDEX
        from viber.models.schema import Census, Content, Deck, Fit, Relation, SkillEntry, Step

        assert len(FIELD_INDEX) == len(FIELD_DOCS)
        documented = {d.path.split(".")[-1] for d in FIELD_DOCS}
        for model in (Census, Deck, Step, SkillEntry, Fit, Relation, Content):
            for fname in model.model_fields:
                assert fname.rstrip("_") in documented, f"{model.__name__}.{fname} undocumented"

    def test_every_documented_limit_exists(self) -> None:
        from viber.models.fields_doc import FIELD_DOCS

        for doc in FIELD_DOCS:
            if doc.limit is not None:
                assert doc.limit in LIMITS, doc.path

    def test_every_artifact_group_is_documented(self) -> None:
        from viber.models.domain import ConfigKey
        from viber.models.fields_doc import FIELD_INDEX

        groups = {p.split(".")[0] for p in FIELD_INDEX}
        assert {
            "frontmatter", "config", "telemetry", "fit", "relation",
            "content", "deck", "step", "skill", "env", "memory", "settled",
            "learnt", "registry",
        } <= groups
        for key in ConfigKey:
            assert f"config.{key.value}" in FIELD_INDEX, key.value
        cols = {"id", "skill", "ts", "step", "phase", "outcome", "note"}
        assert {f"telemetry.invocations.{c}" for c in cols} <= set(FIELD_INDEX)
        fm = {
            "name", "version", "description", "when_to_use", "argument-hint",
            "author", "specialized", "compatibility", "license", "metadata",
            "lint-accept", "disable-model-invocation", "user-invocable", "hooks",
            "updated", "viber",
        }
        assert {f"frontmatter.{k}" for k in fm} <= set(FIELD_INDEX)
        for knob in ("VIBER_RICH", "VIBER_CONFIG_HOME", "NO_COLOR", "COLUMNS", "TERM"):
            assert f"env.{knob}" in FIELD_INDEX, knob

    def test_groups_listing(self, app: Any, census_file: Path) -> None:
        r = call(app, ["fields", "groups", "-nr"], census_file)
        assert r.exit_code == 0
        for probe in ("Group", "telemetry", "frontmatter", "config"):
            assert probe in r.output

    def test_groups_json_shape(self, app: Any, census_file: Path) -> None:
        r = call(app, ["fields", "groups", "-f", "json"], census_file)
        rows = json.loads(r.output)["groups"]
        assert {"telemetry", "config", "frontmatter"} <= {row["group"] for row in rows}
        assert all(row["fields"] > 0 for row in rows)

    def test_group_filter_shows_one_family(self, app: Any, census_file: Path) -> None:
        r = call(app, ["fields", "-G", "telemetry", "-f", "json"], census_file)
        rows = json.loads(r.output)["fields"]
        assert rows and all(row["field"].startswith("telemetry.") for row in rows)
        assert sum(1 for row in rows if row["field"].startswith("telemetry.meta")) == 2

    def test_name_filter_substring(self, app: Any, census_file: Path) -> None:
        r = call(app, ["fields", "-N", "hint", "-f", "json"], census_file)
        rows = json.loads(r.output)["fields"]
        assert rows and all("hint" in row["field"] for row in rows)
        assert any(row["field"] == "relation.long_hint" for row in rows)

    def test_unknown_group_lists_the_groups(self, app: Any, census_file: Path) -> None:
        r = call(app, ["fields", "-G", "nosuch"], census_file)
        assert r.exit_code == 1
        for probe in ("frontmatter", "telemetry", "config"):
            assert probe in r.output

    def test_seed_itself_respects_the_caps(self, app: Any) -> None:
        from conftest import SEED_PATH

        if not SEED_PATH.is_file():
            pytest.skip("seed not present")
        census = load_census(SEED_PATH)
        assert run_limit_checks(census) == []
