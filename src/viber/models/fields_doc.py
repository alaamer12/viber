"""The fields catalog — every field viber works with, explained.

One row per field path of every artifact the CLI reads or writes: the census
JSON `vinit` generates, the SKILL.md frontmatter it ingests, the config.json
layers of the settings chain, and the telemetry database behind stats/next.
For each: what it means, whether it is required, its default, who writes it,
which commands and checks consume it, and its limit from `limits.py` (or none).
`viber fields` is the authoritative face; this table is the single home of the
words. When a field is mentioned anywhere in the CLI — help text, an error, a
doc — it points here.

Order follows the pipeline: census root → decks → lifecycle → skills → fit →
relations → content → history → SKILL.md frontmatter → config layers →
telemetry tables → environment knobs → the .viber memory ledgers and registry
index (regime files the skills write; columns documented for the Router).
Command payloads (REGISTRY keys) are display shape, derived per call and never
persisted — the profile/include system owns those, not this catalog.
"""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class FieldDoc:
    path: str
    ftype: str
    required: bool
    default: str
    written_by: str
    used_by: str
    meaning: str
    limit: str | None = None


def _f(
    path: str,
    ftype: str,
    *,
    required: bool = False,
    default: str = "-",
    written: str,
    used: str,
    meaning: str,
    limit: str | None = None,
) -> FieldDoc:
    return FieldDoc(
        path=path,
        ftype=ftype,
        required=required,
        default=default,
        written_by=written,
        used_by=used,
        meaning=meaning,
        limit=limit,
    )


FIELD_DOCS: Final[tuple[FieldDoc, ...]] = (
    # ---------------------------------------------------- census root
    _f(
        "name", "str", required=True, default="\"viber\"",
        written="seed / vinit when writing the per-project census",
        used="header of every JSON dump; provenance",
        meaning="project slug the census belongs to", limit="project.name",
    ),
    _f(
        "version", "str", default="\"\"", written="seed author",
        used="provenance stamp; shown in json dumps",
        meaning="census format version (not a skill version)", limit="census.version",
    ),
    _f(
        "created", "date-str", default="\"\"", written="init on first census creation",
        used="provenance", meaning="day the per-project census was generated",
        limit="created",
    ),
    _f(
        "createdBy", "str", default="\"\"", written="init", used="provenance",
        meaning="who generated this census (the <USERNAME> of the deck)",
        limit="createdBy",
    ),
    _f(
        "projectPhase", "DR | IP | PP", required=True, default="DR",
        written="`viber set . phase <P>` (phase transitions also log to history)",
        used="status/situation header; the docs posture: DR = provisional (thaw), "
        "IP = formal records; next gating",
        meaning="which project state the lifecycle runs inside",
    ),
    _f(
        "decks", "map<name, Deck>", required=True,
        written="seed / vinit; membership rewritten by `set <skill> deck`",
        used="path resolution (registry), lint membership & deck-conflict, "
        "`deck`, participation",
        meaning="the skill collections the census draws from — "
        "skills live only here and under skills",
    ),
    _f(
        "lifecycle", "list<Step>", required=True,
        written="seed (fixed spine; projects never edit it)",
        used="step/next/situation rosters, current-step detection, "
        "serves validation, lint candidate checks",
        meaning="the five fixed steps: Idea & Understanding → Vision → Foundation "
        "→ Implementation → Shared",
        limit="lifecycle",
    ),
    _f(
        "skills", "map<name, SkillEntry>", required=True,
        written="`add-skill`, `refresh`, `set`; vinit seeds from master",
        used="everything — the census's heart",
        meaning="every known skill with its fit, content, and history", limit="skills",
    ),
    _f(
        "skill.<name>", "slug (map key)", required=True,
        written="`add-skill <name>` — the filesystem slug guard is its cap",
        used="every join: relations, deck membership, step rosters, telemetry",
        meaning="the skill's kebab-case slug — identity of the entry it keys",
        limit="name",
    ),
    _f(
        "unclassified", "list<name | {name,…}>", default="[]",
        written="vinit when it met a foreign/broken skill; `add-skill` never writes it",
        used="status/situation counts; lint unclassified-overlap reads a dict "
        "entry's name key",
        meaning="skills awaiting classification — an honest queue, not a guess",
        limit="unclassified",
    ),
    _f(
        "history", "list<{date,event}>", default="[]",
        written="`set . phase`, `log .`",
        used="provenance trail; no command displays it yet — a skill card's -H "
        "shows the SKILL's ledger, not this one",
        meaning="project-level event ledger; rolling window — oldest evicts on "
        "append, eviction is announced",
        limit="history",
    ),
    _f(
        "notes", "list<{date,text,context}>", default="[]",
        written="global `--note` on a command with no skill target",
        used="project-level notes trail; the card of `.`",
        meaning="notes attached to the project as a whole; rolling window",
        limit="notes",
    ),
    _f(
        "project_id", "str", default="\"\"", written="init / `project create`",
        used="`now`, `--project` resume, the project banner",
        meaning="short location fingerprint of this project's home dir (not sensitive; "
        "record it in docs; re-bind after a move with `viber project link`)",
    ),
    # ---------------------------------------------------- decks.*
    _f(
        "deck.name", "str", default="\"\"", written="seed/vinit",
        used="`deck <name>` card",
        meaning="human label of the deck (\"Amr's Deck\")", limit="deck_name",
    ),
    _f(
        "deck.description", "str", default="\"\"", written="seed/vinit",
        used="`deck <name>` card",
        meaning="what this deck is for, one paragraph", limit="deck_description",
    ),
    _f(
        "deck.mutability", "open | closed", default="open", written="seed/vinit",
        used="doctrine label (closed decks change only through PIPELINE); "
        "no command enforces it yet",
        meaning="whether projects may add members locally",
    ),
    _f(
        "deck.registry", "path | pointer", required=True, written="seed/vinit",
        used="skill_dir_on_disk: relative skill paths resolve against it; "
        "refresh/lint read SKILL.md there",
        meaning="where the deck's skills live on disk (or a pointer file)",
        limit="registry",
    ),
    _f(
        "deck.remote", "url | null", default="null", written="seed/vinit",
        used="`lint --remote` compares the clone at registry against origin HEAD",
        meaning="the git remote the deck ships from",
    ),
    _f(
        "deck.skills", "list<name>", default="[]",
        written="add-skill/remove-skill/set deck (kept sorted)",
        used="lint membership & cross-deck conflict, `deck` listing",
        meaning="who belongs to this deck — the participation gate",
        limit="deck.skills",
    ),
    # ---------------------------------------------------- lifecycle steps
    _f(
        "step.step", "str", required=True, written="seed (fixed spine)",
        used="the join key: fit.serves, `step <name>`, next/situation current step",
        meaning="step name", limit="step_name",
    ),
    _f(
        "step.phase", "DR | IP | PP | null", default="null", written="seed",
        used="project-phase mapping (DR steps are drafting); null = phase-blind "
        "shared step",
        meaning="which project state this lifecycle step lives in",
    ),
    _f(
        "step.goal", "str", default="\"\"", written="seed",
        used="`step` output, situation fallback",
        meaning="one sentence of intent for the step", limit="goal",
    ),
    _f(
        "step.needs", "list<str>", default="[]", written="seed",
        used="`step --needs`, and `next` when no skill is unblocked — "
        "needs stand on their own",
        meaning="the capabilities this step must accomplish, skill or no skill",
        limit="needs",
    ),
    _f(
        "step.possible_skills", "list<name>", default="[]",
        written="seed (favorite-deck pool)",
        used="`step` shows uninstalled candidates; lint warns when one is "
        "absent from the census",
        meaning="declared useful candidates for the step — suggestions, never blockers",
        limit="possible_skills",
    ),
    _f(
        "step.commands", "list<name>", default="[]", written="seed",
        used="roster rows marked 'command'; `next` lists them when nothing is unblocked",
        meaning="viber's own v-commands declared at this step", limit="commands",
    ),
    # ---------------------------------------------------- skills.*
    _f(
        "skill.version", "dot-str | null", written="`refresh` from SKILL.md frontmatter",
        used="rosters show '?' when null; lint version-drift vs disk",
        meaning="the skill's own version as last observed on disk", limit="version",
    ),
    _f(
        "skill.type", "battery|meta|normal|hybrid|otherwise", default="normal",
        written="`set <skill> type` (closed enum, rejected at load otherwise)",
        used="classification on the card; `list --by`/`--filter` grouping",
        meaning="what kind of skill this is; otherwise = honestly unclassifiable",
    ),
    _f(
        "skill.description", "str", default="\"\"",
        written="`refresh` from frontmatter (over-cap refresh rejected with the identity)",
        used="skill card panel; `--brief` line",
        meaning="one-paragraph summary — body lives in SKILL.md",
        limit="description",
    ),
    _f(
        "skill.use_cases", "list<str>", default="[]",
        written="`set <skill> use_cases`",
        used="next/router/vinit judge fit by evidence, not name",
        meaning="concrete situations the skill applies to", limit="use_cases",
    ),
    _f(
        "skill.use_cases[]", "str (item)", default="[]", written="`set <skill> use_cases`",
        used="lint checks each case line against the item cap",
        meaning="one situation that fits the skill, in a phrase", limit="use_case",
    ),
    _f(
        "skill.deck", "deck-name | null",
        written="add-skill / `set <skill> deck` (lint conflict resolution)",
        used="path resolution layer, participation gate, lint membership",
        meaning="which deck owns this entry — must exist in decks",
    ),
    _f(
        "skill.path", "rel-path | null",
        written="add-skill / `set <skill> path` (validated: SKILL.md must exist)",
        used="refresh, lint broken-path/version-drift, `skill --path`",
        meaning="absolute realpath in initialized projects; seed paths may be deck-relative",
        limit="path",
    ),
    _f(
        "skill.owned", "bool", default="false",
        written="add-skill false; true for the project's own five",
        used="skill_dir_on_disk: owned paths resolve against the census dir, "
        "not the deck registry",
        meaning="whether the project itself owns the skill files",
    ),
    _f(
        "skill.recurring", "bool", default="false",
        written="seed / `set <skill> recurring`",
        used="the next/situation REVISIT pool",
        meaning="skill is meant to be revisited as the project clarifies; once used but "
        "never ok'd it re-surfaces cross-step until an ok settles it",
    ),
    _f(
        "skill.content", "{entry,references,assets,examples}", default="empty",
        written="`refresh` re-lists from disk",
        used="`skill --content` / the card's file manifest",
        meaning="the manifest of files that compose the skill — index, not copy",
    ),
    _f(
        "skill.fit", "Fit", default="empty",
        written="seed (master), `set doing/why/blockers/...`",
        used="next/situation/step — the behaviour block the router reads",
        meaning="everything the census knows about how this skill fits work",
    ),
    _f(
        "skill.history", "list<{date,event}>", default="[]",
        written="log / refresh / set-deck / set-path (rolling)",
        used="the card's history section; audit trail",
        meaning="per-skill event ledger; oldest evicts past the cap, eviction announced",
        limit="history",
    ),
    _f(
        "skill.notes", "list<{date,text,context}>", default="[]",
        written="`note --on` / global `--note` on use/outcome/set/log/skill",
        used="the card's notes section; the REVISIT reason line",
        meaning="the agent's own notes on this skill; rolling window, eviction announced",
        limit="notes",
    ),
    # ---------------------------------------------------- skill.fit.*
    _f(
        "fit.role", "str", default="\"\"", written="seed/vinit", used="skill card",
        meaning="one line: where this skill sits in the web of work", limit="role",
    ),
    _f(
        "fit.when", "str", default="\"\"", written="seed/vinit",
        used="`next` when-line; suggestions context",
        meaning="the trigger moment — when this is the right skill", limit="when",
    ),
    _f(
        "fit.doing", "str", default="\"\"",
        written="vinit per project (`set <skill> doing`) — mandatory for serving skills",
        used="`next`/`situation` print it as the `do:` line",
        meaning="what exactly doing this skill means in THIS project, concretely",
        limit="doing",
    ),
    _f(
        "fit.why", "str", default="\"\"",
        written="vinit per project (`set <skill> why`) — mandatory for serving skills",
        used="`next`/`situation` print it as the `why it exists here` line",
        meaning="why this skill may be a next step here, in this project's terms",
        limit="why",
    ),
    _f(
        "fit.phase", "DR | IP | PP | null", default="-",
        written="`set <skill> phase <P|null>`",
        used="recorded per skill; no command consumes it back yet — stated honestly",
        meaning="the project phase this skill is assigned to in this census",
    ),
    _f(
        "fit.serves", "list<step>", default="[]",
        written="vinit per project / add-skill --serve",
        used="roster membership (step/situation/next), lint dangling-serves",
        meaning="which steps of the spine this skill actually serves here",
        limit="serves",
    ),
    _f(
        "fit.produces", "list<str>", default="[]", written="seed/vinit",
        used="next do:-composition when doing is absent; consumes/produces evidence",
        meaning="artifacts the skill creates", limit="produces",
    ),
    _f(
        "fit.consumes", "list<str>", default="[]", written="seed/vinit",
        used="`next` consumes line",
        meaning="artifacts the skill reads as input", limit="consumes",
    ),
    _f(
        "fit.blockers", "list<str>", default="[]",
        written="`set <skill> blockers`",
        used="ready/blocked everywhere (roster, status, next); lint null-path pairing; "
        "the surface deferred questions live on",
        meaning="named walls that stop this skill now", limit="blockers",
    ),
    _f(
        "fit.blockers[]", "str (item)", default="[]", written="`set <skill> blockers`",
        used="lint checks each wall against the item cap — one blocker names one wall",
        meaning="a single named wall", limit="blocker",
    ),
    _f(
        "fit.produces[]", "str (item)", default="[]", written="seed/vinit",
        used="lint artifact-item cap check",
        meaning="one artifact the skill creates", limit="artifact",
    ),
    _f(
        "fit.consumes[]", "str (item)", default="[]", written="seed/vinit",
        used="lint artifact-item cap check",
        meaning="one artifact the skill reads", limit="artifact",
    ),
    _f(
        "step.needs[]", "str (item)", default="[]", written="seed",
        used="lint artifact-item cap check",
        meaning="one capability the step must accomplish", limit="artifact",
    ),
    _f(
        "fit.after", "list<Relation>", default="[]",
        written="seed (authored once, mirrored both ends)",
        used="topological roster order AND `next` reason lines (via hints)",
        meaning="predecessor edges: what should run first", limit="after",
    ),
    _f(
        "fit.before", "list<Relation>", default="[]",
        written="seed (mirror of the other skill's after)",
        used="card relations block",
        meaning="what this skill feeds", limit="before",
    ),
    _f(
        "fit.with", "list<Relation>", default="[]", written="seed",
        used="card relations block; pairing evidence",
        meaning="natural companions, no ordering implied", limit="with",
    ),
    # ---------------------------------------------------- relations & records
    _f(
        "relation.skill", "name", required=True, written="seed",
        used="lint dangling-relation; the edge endpoint",
        meaning="the other skill of an edge",
    ),
    _f(
        "relation.hint", "str", default="\"\"", written="seed",
        used="`next` reason lines",
        meaning="one line: why this edge exists", limit="hint",
    ),
    _f(
        "relation.long_hint", "str", default="\"\"", written="seed",
        used="`next` long detail under a reason; --long on cards",
        meaning="the use-case the edge covers", limit="long_hint",
    ),
    _f(
        "content.entry", "path", default="SKILL.md", written="add-skill / refresh",
        used="--content manifest first line",
        meaning="the skill's main file",
    ),
    _f(
        "content.references", "list<path>", default="[]", written="refresh",
        used="--content manifest",
        meaning="reference docs the skill loads on demand",
    ),
    _f(
        "content.assets", "list<path>", default="[]", written="refresh",
        used="--content manifest",
        meaning="templates/diagrams the skill carries",
    ),
    _f(
        "content.examples", "list<path>", default="[]", written="refresh",
        used="--content manifest",
        meaning="worked examples",
    ),
    _f(
        "history[].date", "date-str", required=True, written="CLI (today UTC)",
        used="card history lines",
        meaning="day of the event", limit="date",
    ),
    _f(
        "history[].event", "str", required=True, written="CLI",
        used="card history; eviction messages reference it",
        meaning="one dated sentence", limit="event",
    ),
    _f(
        "skill.notes[].text", "str", required=True, written="`note`/`--note`",
        used="card notes; REVISIT reason",
        meaning="the note itself, one dated line", limit="note",
    ),
    _f(
        "skill.notes[].date", "date-str", required=True, written="CLI (today UTC)",
        used="card notes lines", meaning="day the note was written", limit="date",
    ),
    _f(
        "skill.notes[].context", "str", written="the command that recorded it",
        used="card notes lines",
        meaning="which command attached the note (use/outcome/set/note/...)",
    ),
    # ---------------------------------------------------- SKILL.md frontmatter
    # What parse_frontmatter reads from each skill's header — the census's sources.
    _f(
        "frontmatter.name", "str", required=True, written="the skill author (SKILL.md header)",
        used="the agent harness resolves the skill by it; viber itself keys on the deck slug",
        meaning="the skill's declared name",
    ),
    _f(
        "frontmatter.version", "dot-str", written="the skill author",
        used="`add-skill`/`refresh` copy it into skill.version (over-cap rejected at the "
        "read); lint version-drift compares it against the census",
        meaning="the skill's own release tag — disk truth the census trails",
        limit="version",
    ),
    _f(
        "frontmatter.description", "str", required=True, written="the skill author",
        used="`add-skill`/`refresh` copy it into skill.description "
        "(over-cap frontmatter is rejected with the identity)",
        meaning="the one-paragraph summary shown before the body loads",
        limit="description",
    ),
    _f(
        "frontmatter.when_to_use", "str", written="the skill author",
        used="registry export uses it before description trigger/first-sentence fallback; "
        "refresh preserves the separately curated fit.when",
        meaning="when the harness should invoke this skill",
    ),
    _f(
        "frontmatter.argument-hint", "str", written="the skill author",
        used="harness hint at invocation; not read by viber",
        meaning="expected arguments for the slash command",
    ),
    _f(
        "frontmatter.author", "str", written="the skill author",
        used="human attribution inside the deck; not read by viber",
        meaning="who wrote this skill",
    ),
    _f(
        "frontmatter.specialized", "name | none", written="the skill author",
        used="deck authoring/routing convention; not read by viber",
        meaning="the technology domain the skill is bound to — 'none' is "
        "platform-neutral; 'specialized/' children name their domain "
        "(scss, tailwind, daisyui, git, win32)",
    ),
    _f(
        "frontmatter.compatibility", "str", written="the skill author",
        used="read by agents before running the skill; not read by viber",
        meaning="runtime requirements: interpreter versions, host features, "
        "what is optional",
    ),
    _f(
        "frontmatter.license", "SPDX-id", written="the skill author",
        used="legal cover for the skill and any bundled scripts; not read by viber",
        meaning="the license the skill ships under",
    ),
    _f(
        "frontmatter.metadata", "map<key, value>", written="the skill author",
        used="author notes for humans and agents; safe parsing preserves this mapping, "
        "but it is not copied into the census",
        meaning="one open namespace for provenance notes — seen on disk: inspired_by, "
        "catalog_last_verified, attribution, relationship, combines, version, author, "
        "compatibility, tags, source, category, role",
    ),
    _f(
        "frontmatter.lint-accept", "map<exception, reason>", written="the skill author",
        used="the deck's structural lint ends its argument here; viber never reads it",
        meaning="accepted-by-design exceptions, each with the reason that "
        "settles the fight ('Keep as-is.')",
    ),
    _f(
        "frontmatter.disable-model-invocation", "bool", written="the skill author",
        used="harness gate: the model must not pick this skill on its own; "
        "viber never reads it",
        meaning="true marks a user-only-invocation skill",
    ),
    _f(
        "frontmatter.user-invocable", "bool", written="the skill author",
        used="harness gate on slash availability; viber never reads it",
        meaning="whether the user may invoke the skill directly",
    ),
    _f(
        "frontmatter.hooks", "nested map", written="the skill author",
        used="host harness hook wiring (e.g. Stop -> hooks -> command/timeout); "
        "safe frontmatter parsing preserves nesting, but viber never executes hooks",
        meaning="commands the host runs at hook points",
    ),
    _f(
        "frontmatter.updated", "date", written="the skill author / deck tooling",
        used="staleness signal read by humans and deck tooling; viber never reads it",
        meaning="last touched day (YYYY-MM-DD)",
    ),
    _f(
        "frontmatter.viber", "part | separated | excluded", written="the skill author",
        used="supervision umbrella membership declared on the skill "
        "(spec: supervision.md 4, router.md); deck membership stays the primary gate; "
        "no SKILL.md carries the tag yet",
        meaning="whether the skill's relocatable output reroutes under .viber/",
    ),
    # ---------------------------------------------------- config.json layers
    # The five chain keys of .viber/.data/config.json and the user file (config.md owns
    # the chain; these rows state what each key IS and who consumes it).
    _f(
        "config.census", "path", written="`viber config set census <path>` (-u for the user layer)",
        used="settings resolution locates the census through it (flag > env > project > user)",
        meaning="where this project's census JSON lives",
    ),
    _f(
        "config.project", "project-id", written="`viber project use <id>` (user layer)",
        used="Globals resolution: --project > env VIBER_PROJECT > this default > CWD",
        meaning="the default project id to resume when no census path is given",
    ),
    _f(
        "config.profile", "minimal | standard | full", written="`viber config set profile <P>`",
        used="default field selection of every command (output/fields.py groups)",
        meaning="how much of each payload viber shows by default",
    ),
    _f(
        "config.format", "text | json", written="`viber config set format <f>`",
        used="default output format of every command",
        meaning="human text or machine json, chosen per machine",
    ),
    _f(
        "config.telemetry", "bool", written="`viber config set telemetry <true|false>`",
        used="gates whether `use`/`outcome` record rows; off leaves stats empty",
        meaning="the usage-tracking switch",
    ),
    _f(
        "config.plugins", "bool", written="`viber config set plugins <true|false>`",
        used="gates loading .viber/plugins/*.py — off by default: a machine runs no "
        "code it did not explicitly enable",
        meaning="the internal-extension switch (registry seam)",
    ),
    # ---------------------------------------------------- telemetry database
    # .viber/.data/telemetry.db (next to the census): one row per recorded call.
    _f(
        "telemetry.invocations.id", "int", required=True, written="SQLite autoincrement",
        used="the UPDATE target of `outcome` closing the newest open row",
        meaning="row identity of one recorded invocation",
    ),
    _f(
        "telemetry.invocations.skill", "name", required=True, written="`viber use <skill>`",
        used="stats/patterns grouping, `next` successor hints, the `last:` line",
        meaning="which skill this invocation is about",
    ),
    _f(
        "telemetry.invocations.ts", "ISO datetime", required=True,
        written="`use`/`outcome` (UTC, now_iso)",
        used="lastUsed columns, row ordering, `stats --since`",
        meaning="when the invocation was recorded",
    ),
    _f(
        "telemetry.invocations.step", "str | null",
        written="`viber use` (the step at the time; `--step-override/-s` records any name)",
        used="the step shown on the `last:` line",
        meaning="lifecycle step active when this ran",
    ),
    _f(
        "telemetry.invocations.phase", "str | null", written="`viber use` (the phase at the time)",
        used="stored as context; no command reads it back yet — stated honestly",
        meaning="project phase when this ran",
    ),
    _f(
        "telemetry.invocations.outcome", "ok | fail | skip | null",
        written="`viber outcome <skill> <ok|fail|skip>` closes the newest open row",
        used="ok/fail counts in stats, `last_done` only sees closed rows",
        meaning="how it ended; null means still open",
    ),
    _f(
        "telemetry.invocations.note", "str | null",
        written="`viber outcome <skill> <result> [note]` (positional)",
        used="kept with the closed row for human reading",
        meaning="one free-text line about the outcome",
    ),
    _f(
        "telemetry.meta.key", "str", required=True, written="seeded automatically on connect",
        used="currently one key: schema_version",
        meaning="config keys the database carries with it",
    ),
    _f(
        "telemetry.meta.value", "str", required=True, written="seeded automatically",
        used="read for schema versioning",
        meaning="the stored value of a meta key",
    ),
    # ---------------------------------------------------- environment knobs
    # Read-only surface: what the shell may set; no command writes these.
    _f(
        "env.VIBER_CENSUS", "path", written="the user's shell",
        used="settings chain env layer (core/settings.py) — overrides project/user config",
        meaning="env override of the census key",
    ),
    _f(
        "env.VIBER_PROJECT", "project-id", written="the user's shell",
        used="Globals resolution env layer — resumes that project's data over cwd",
        meaning="env override of the project key (a location-fingerprint id)",
    ),
    _f(
        "env.VIBER_PROFILE", "minimal | standard | full", written="the user's shell",
        used="settings chain env layer",
        meaning="env override of the profile key",
    ),
    _f(
        "env.VIBER_FORMAT", "text | json", written="the user's shell",
        used="settings chain env layer",
        meaning="env override of the format key",
    ),
    _f(
        "env.VIBER_TELEMETRY", "true | false", written="the user's shell",
        used="settings chain env layer",
        meaning="env override of the telemetry switch",
    ),
    _f(
        "env.VIBER_PLUGINS", "true | false", written="the user's shell",
        used="settings chain env layer",
        meaning="env override of the plugins switch",
    ),
    _f(
        "env.VIBER_CONFIG", "path", written="the user's shell",
        used="config_store.locate — redirects the PROJECT config file itself",
        meaning="explicit path to the project config.json",
    ),
    _f(
        "env.VIBER_CONFIG_HOME", "path", written="the user's shell",
        used="config_store.locate — redirects the USER config dir",
        meaning="explicit directory holding the user config.json",
    ),
    _f(
        "env.VIBER_RICH", "1 | 0 | true | false", written="the user's shell",
        used="display.resolve_display — forces layout; a bad value warns and "
        "falls to auto (reads never brick)",
        meaning="the per-machine display switch (force-ON lives only here)",
    ),
    _f(
        "env.NO_COLOR", "any value", written="the user's shell / terminal",
        used="rich honors it directly — color axis only, layout unchanged",
        meaning="industry-standard no-color request",
    ),
    _f(
        "env.COLUMNS", "int", written="the user's shell",
        used="display.resolve_width — explicit width before terminal size",
        meaning="forced render width (clamped 60-240)",
    ),
    _f(
        "env.TERM", "terminal kind", written="the user's shell",
        used="display auto-detection — 'dumb' forces plain; the empty string "
        "does NOT (verified Windows fact)",
        meaning="what kind of terminal believes it is",
    ),
    # ---------------------------------------------------- memory ledgers
    # .viber/ tables under the regime's own discipline (docs/regime/memory.md owns
    # the shapes; the CLI never writes them — skills do). Columns as the tables have them.
    _f(
        "memory.num", "M<n>", written="vinit / grill-me sessions",
        used="the row handle questions get re-asked by",
        meaning="ordinal of one open or deferred question",
    ),
    _f(
        "memory.question", "str", written="vinit / grill-me sessions",
        used="Router resurfaces open questions when blockers clear",
        meaning="what is being asked",
    ),
    _f(
        "memory.clarification", "str", written="vinit / grill-me sessions",
        used="context for answering it well",
        meaning="description / what the question means",
    ),
    _f(
        "memory.blocks", "str", written="vinit / grill-me sessions",
        used="what unblocks it — the surfacing condition",
        meaning="what blocks it now",
    ),
    _f(
        "memory.raised", "date", written="vinit / grill-me sessions",
        used="age of the open question",
        meaning="day it was asked",
    ),
    _f(
        "memory.status", "open | deferred", written="the session",
        used="deferred items surface when unblocked",
        meaning="state of the question",
    ),
    _f(
        "settled.num", "S<n>", written="the session that got the answer",
        used="row handle; Question columns mirror the memory row it settles",
        meaning="ordinal of one answered question",
    ),
    _f(
        "settled.question", "str", written="the session",
        used="so the answer is found by the question it closes",
        meaning="the settled question",
    ),
    _f(
        "settled.answer", "str", written="the user's decision",
        used="Router avoids re-suggesting settled decisions",
        meaning="the answer as given",
    ),
    _f(
        "settled.reason", "str", written="the session",
        meaning="why — explicit instruction or implicit read",
        used="re-litigation fuel check before re-asking",
    ),
    _f(
        "settled.kind", "explicit | implicit", written="the session",
        used="how firmly the answer binds",
        meaning="whether the user said it or it was inferred",
    ),
    _f(
        "settled.settled", "date", written="the session",
        used="age of the decision",
        meaning="day it closed",
    ),
    _f(
        "settled.provisional", "bool", written="the session",
        used="a provisional answer may be re-opened; a firm one must not",
        meaning="whether the decision is still draft (thaw posture)",
    ),
    _f(
        "learnt.num", "L<n>", written="the session",
        used="row handle",
        meaning="ordinal of one learned fact",
    ),
    _f(
        "learnt.fact", "str", written="the session",
        used="shapes future decisions",
        meaning="what was learned about the user or project",
    ),
    _f(
        "learnt.evidence", "str", written="the session",
        used="so the fact can be re-checked, not just trusted",
        meaning="user said / observed / verified, with source",
    ),
    _f(
        "learnt.implication", "str", written="the session",
        used="how it should shape decisions",
        meaning="what follows from the fact",
    ),
    _f(
        "learnt.learnt", "date", written="the session",
        used="age of the fact",
        meaning="day it was learned",
    ),
    _f(
        "registry.viber", "part | separated | excluded",
        written="/viber init when indexing the deck; /adapt for project additions",
        used="Router candidate search; supervision's rerouting gate "
        "(supervision.md owns the rule)",
        meaning="each skill's participation column in .viber/registry.md",
    ),
)

FIELD_INDEX: Final[dict[str, FieldDoc]] = {d.path: d for d in FIELD_DOCS}
