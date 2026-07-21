# Dify 1.16.0 Compatibility Evaluation

Evaluation date: 2026-07-21

## Baseline

- Dify tag: `1.16.0`
- Dify commit: `5c6372d2f76d240265b92fd27c16bc772ffcb107`
- Dify source checkout: complete Git history, not a shallow clone
- Declared App DSL version: `0.7.0`
- Scenario suite: `examples/dify-1.16.0/*.yml`

## What Was Exercised

The source-backed gate loads Dify 1.16.0's own Python 3.12 code and validates:

- `CURRENT_APP_DSL_VERSION`;
- marketplace/package/GitHub dependency DTOs;
- all graph node payloads through Dify's registered production node classes;
- Human Input through Dify's workflow graph validation path;
- portable `AgentPackage` objects;
- Agent v2 `WorkflowNodeJobConfig` objects;
- Agent App and Agent v2 package references.

This is stronger than validating against a copied schema because the checks run
the exact Pydantic models and node registry shipped by the tagged Dify source.

The import gate then calls Dify 1.16.0's real `AppDslService.import_app` against
isolated PostgreSQL and Redis instances. It persists App, Workflow, Agent,
Agent-package, variable, and dependency state through Dify's normal service
path. The app-created event signal is suppressed so unrelated trigger/plugin
side effects do not require a plugin daemon.

The Console UI gate starts the exact Dify 1.16.0 source and imports three
representative files through the browser: priority routing, array iteration,
and the Agent v2 workflow. Dify rendered their real graph canvases, including
the Iteration container and the selected Agent v2 inline-configuration panel.
The resulting screenshots are checked into `assets/workflow-previews/`.

## Scenario Results

| # | Scenario | Important nodes/features | Local strict | Dify models | DB import |
| --- | --- | --- | --- | --- | --- |
| 01 | Text summarizer | Start, LLM, End | Pass | Pass | Pass |
| 02 | Multi-turn assistant | Advanced Chat, `sys.query`, memory, Answer | Pass | Pass | Pass |
| 03 | Excel to Markdown analysis | File input, Document Extractor, Code, LLM | Pass | Pass | Pass |
| 04 | Priority routing | IF/ELSE, Template Transform, Variable Aggregator | Pass | Pass | Pass |
| 05 | Customer-service classifier | Question Classifier, three Answer branches | Pass | Pass | Pass |
| 06 | Batch formatting | Code, Iteration, container child topology | Pass | Pass | Pass |
| 07 | Quality loop | Loop, loop variable, Assigner v2 | Pass | Pass | Pass |
| 08 | Human approval | Human Input, select/file-list inputs, action branches | Pass | Pass | Pass |
| 09 | Agent v2 workflow | Portable package, binding, job, declared output | Pass | Pass | Pass |
| 10 | Agent App | `app.mode: agent`, package Soul and model | Pass | Pass | Pass |

Import summary: 10 completed, 0 failed, 0 warnings. Dify persisted nine graph
apps with one draft Workflow each and one standalone Agent App.

## Defect Found And Fixed

The existing `advanced-chat-0.7.yml` fixture omitted `data.context` on its LLM
node. The project validator accepted it, but Dify 1.16's `LLMNodeData` rejected
it because `context` is required.

The local validator now emits `node.llm.context`, valid 0.6.0/0.7.0 fixtures
include the field, and a dedicated invalid fixture prevents regression.

## Reproduce

First run the repository gate:

```bash
python3 scripts/validate_dsl.py \
  --strict \
  --target-version 0.7.0 \
  examples/dify-1.16.0/*.yml
```

Then run the source-backed gate with Dify's Python 3.12 API environment:

```bash
python scripts/validate_with_dify_source.py \
  --dify-source /path/to/dify-1.16.0 \
  examples/dify-1.16.0/*.yml
```

## Remaining Workspace Validation

The following checks still require a configured Dify 1.16.x workspace:

- save/re-export round trips for the full ten-scenario suite;
- plugin installation and exact marketplace identifier availability;
- model credentials and model availability;
- Agent credentials, contacts, skills, files, and other omitted assets;
- execution semantics, generated files, external APIs, and Human Input delivery;
- UI rendering for workspace-bound plugins, models, and omitted assets.

The evaluation intentionally does not call models, install plugins, access
external APIs, or execute workflow side effects.
