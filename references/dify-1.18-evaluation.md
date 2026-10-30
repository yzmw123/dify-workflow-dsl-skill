# Dify 1.18 compatibility evaluation

Date: 2026-10-30

## Baseline and results

- Official Dify tag: `1.18.0`
- Commit: `50abea97062110044f15d0e03ccecadd9ccc87ca`
- App DSL: `0.7.0`
- Source environment: Python 3.13 with the tag's frozen API dependency lock.
- Local regression: **54 tests passed** (Python 3.14).
- Static strict validation: legacy 0.6 fixtures under the 1.15 profile; legacy
  0.7 fixtures and ten scenarios under 1.16; ten existing plus four new
  scenarios under 1.18. All passed without diagnostics.
- Official source gate: **14/14 passed** using Dify's production node registry,
  graph validation, Agent package/job models, route execution completeness,
  Agent App envelope, and Site model.
- Additional source compatibility checks: a legacy plugin Agent using
  `version: "2"` and missing config files/skills using `file_id: null` both
  passed. A non-string node type was rejected without aborting the batch;
  all 16 valid documents following it were still checked successfully.
- Real database import: **14/14 persisted, 0 failures** through
  `AppDslService.import_app`. Twelve completed without warnings; two completed
  with three expected workspace-resource warnings, listed below.
- Installed skill: clean runtime preparation, execution from a different working
  directory with spaces in the installation path, JSON output, and offline cache
  reuse passed. Missing offline runtime returns an actionable error without
  attempting installation. A venv created without pip was repaired, populated
  with dependencies, and reused offline successfully. Forced installation into
  the source, a source alias, a source parent, or a managed resource subdirectory
  was rejected with source files preserved.
- Skill metadata validation, shell syntax, and whitespace checks passed.

The import environment used dedicated PostgreSQL 16 and Redis 7 containers,
loopback-only ports, a new test tenant/account, and the complete Dify 1.18
database migration chain. Normal app creation handlers were enabled. No model
calls, plugin installation, workflow execution, or external API operations were
performed. See [recorded import results](validation/dify-1.18-import-results.json).

## New scenarios

| File | Coverage | Source model | Database import |
| --- | --- | --- | --- |
| `01-agent-text.yml` | System `text` output without custom declarations | Pass | Completed |
| `02-agent-routes.yml` | Two output routes, custom `summary`, `text` and `switch` selectors | Pass | Completed |
| `03-agent-knowledge-skills.yml` | Workspace skill, KnowledgeFS binding, portable Site settings | Pass | Completed with 2 warnings |
| `04-knowledge-retrieval-v2.yml` | Native retrieval node, query selector, `result` output | Pass | Completed with 1 warning |

The two warning-bearing examples intentionally contain synthetic references:

- `agent_knowledge_fs_rebind_required`: select a real Agent Knowledge Base.
- `agent_workspace_skill_unresolved`: select/install the `support-guide` skill.
- `knowledge_fs_space_unresolved`: select a real retrieval space before publishing.

These are destination-workspace setup requirements, not evidence of runnable
knowledge/skill execution in an unconfigured workspace.

## Regression coverage

Checks exercise explicit Dify targets, default target selection, patch suffixes,
unsupported targets, old-version rejection of new fields, legacy Agent output
semantics, 1.18 reserved output names, route IDs and conditions, matching route
representations, invalid branch handles, missing route coverage, route/error
strategy conflicts, workspace skill types, knowledge binding identities and
limits, retrieval configuration, Site fields, binary package input, and
installation/runtime recovery. Existing graph, container, Human Input, plugin,
selector, and SQL checks are retained.

Regression cases also cover legacy plugin Agent version discrimination,
disabled-route stale edges, missing-asset null IDs without mutating the input,
production resolver compatibility with the 1.16 signature, malformed node
types and app modes, pip restoration, and source-directory installation guards.
The source gate delegates node dispatch to Dify's production resolver so its
legacy Agent handling matches the selected checkout.

An independent forward test also authored a new routed support workflow for
1.18 and a custom-output Agent workflow for 1.16. The 1.18 workflow passed the
official source gate. Output selectors matched the official
`text / switch / summary` projection, and version/selector/branch negative
cases were rejected. Offline installed-skill reuse passed.

## Reproduce

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v

python3 scripts/run_validator.py --strict --dify-version 1.15 tests/fixtures/valid-0.6/*.yml
python3 scripts/run_validator.py --strict --dify-version 1.16 examples/dify-1.16.0/*.yml
python3 scripts/run_validator.py --strict --dify-version 1.18 examples/dify-1.16.0/*.yml examples/dify-1.18.0/*.yml

/path/to/dify-1.18.0/api/.venv/bin/python scripts/validate_with_dify_source.py \
  --dify-source /path/to/dify-1.18.0 --dify-version 1.18.0 \
  examples/dify-1.16.0/*.yml examples/dify-1.18.0/*.yml
```

For the database gate, provision dedicated PostgreSQL/Redis instances and apply
the official Dify migrations using its API environment. Set explicit loopback
`DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_DATABASE`, `REDIS_HOST`,
`REDIS_PORT`, and `REDIS_PASSWORD`. The test database name must begin with
`dify_skill_`. Use a temporary `STORAGE_LOCAL_PATH`; the gate selects local
storage explicitly so all generated runtime files stay there. Then run:

```bash
/path/to/dify-1.18.0/api/.venv/bin/python tests/integration/validate_dify_import.py \
  --dify-source /path/to/dify-1.18.0 --report /tmp/dify-import-results.json
```

The integration gate creates test records and leaves cleanup to the owner of
those isolated services. It does not start services or run migrations itself.

## Remaining workspace checks

This update does not certify model responses, external tools, KnowledgeFS
service availability, real skill/file contents, publishing, UI save/re-export
round trips, or `.ifpkg` resource reconstruction. Those require a configured
target workspace. The 1.15/1.16 profiles were regression-tested locally; their
server environments were not redeployed for this evaluation. Historical 1.16
import evidence remains in [the 1.16 report](dify-1.16-evaluation.md).

CI now includes Python 3.10, 3.12, and 3.13 plus cold installation/offline reuse;
remote CI results require a subsequent push and are not part of these local results.
