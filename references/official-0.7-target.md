# Official DSL 0.7.0 Target

Use this reference for new DSL targeting Dify 1.16.x. The rules were checked
against the `1.16.0` source tag on 2026-07-20. DSL 0.6.0 remains supported as a
compatibility target; see `official-0.6-target.md`.

## Source Baseline

- Version constant (`CURRENT_APP_DSL_VERSION = "0.7.0"`):
  <https://github.com/langgenius/dify/blob/1.16.0/api/constants/dsl_version.py>
- App import/export and mode dispatch:
  <https://github.com/langgenius/dify/blob/1.16.0/api/services/app_dsl_service.py>
- Portable Agent package entities:
  <https://github.com/langgenius/dify/blob/1.16.0/api/services/agent/dsl_entities.py>
- Agent package export/import rewrite:
  <https://github.com/langgenius/dify/blob/1.16.0/api/services/agent/dsl_service.py>
- Agent v2 node data and runtime job models:
  <https://github.com/langgenius/dify/blob/1.16.0/api/core/workflow/nodes/agent_v2/entities.py>
  and
  <https://github.com/langgenius/dify/blob/1.16.0/api/models/agent_config_entities.py>
- Human Input schema:
  <https://github.com/langgenius/dify/blob/1.16.0/api/core/workflow/nodes/human_input/entities.py>
- AI workflow generator and deterministic validator:
  <https://github.com/langgenius/dify/tree/1.16.0/api/core/workflow/generator>

The preceding `1.15.0` tag declares DSL `0.6.0`. Therefore this skill maps Dify
1.15.x to 0.6.0 and Dify 1.16.x to 0.7.0.

## What Changed From 0.6.0

0.7.0 is not merely a version-string bump. Dify 1.16 adds portable Agent
composition to the App DSL:

- `app.mode: agent` is a supported top-level Agent App mode.
- Top-level `agent` points to an entry in `agent_packages`.
- Workflow/Chatflow exports can carry `agent_packages` for portable Agent v2
  nodes.
- Agent v2 node bindings are rewritten to package refs during export and back to
  workspace bindings during import.
- Human Input has a structured form/action schema and action-based edge handles.

Ordinary Workflow and Chatflow graph structure remains compatible enough that a
well-formed 0.6.0 graph can usually be authored as 0.7.0, but migration should
still be validated and import-tested.

## Standard Graph App

```yaml
version: "0.7.0"
kind: app
app:
  name: "App name"
  mode: workflow           # or advanced-chat
dependencies: []
workflow:
  conversation_variables: []
  environment_variables: []
  graph:
    nodes: []
    edges: []
```

Use `end` as the normal Workflow terminal and `answer` as the Chatflow terminal.
A trigger-based side-effect Workflow can intentionally omit `end`, but then it
does not return normal outputs to a caller.

## Top-Level Agent App

```yaml
version: "0.7.0"
kind: app
app:
  name: "Research Agent"
  mode: agent
agent:
  package_ref: agent_1
agent_packages:
  agent_1:
    schema_version: 1
    metadata:
      name: "Research Agent"
      description: ""
      role: researcher
      icon_type: emoji
      icon: "🔎"
      icon_background: "#E4FBCC"
    soul:
      schema_version: 1
    omitted_assets: []
dependencies: []
```

`agent.package_ref` must resolve to an `agent_packages` key. `metadata.name` is
required and has a 255-character maximum. `description` and `role` default to
empty strings. `soul` is an Agent Soul config with `schema_version: 1`.
Agent package, metadata, Soul top-level, and omitted-asset objects reject unknown
fields according to their Dify 1.16 Pydantic schemas.

Portable exports deliberately sanitize sensitive or workspace-bound values:

- credential, secret, password, token, and API-key fields are removed/nullified;
- model and tool credential refs are cleared;
- uploaded Agent skill/file IDs are cleared and listed as missing;
- human contact/workspace IDs are cleared;
- omitted skill/file assets are described in `omitted_assets`, not embedded.

An imported Agent package can therefore succeed with warnings and still require
the user to reconnect credentials, files, skills, contacts, or other assets.

## Agent Package Omitted Assets

```yaml
omitted_assets:
  - kind: skill            # skill | file
    name: "research-guide.md"
    size: 2048
    hash: "..."            # optional
    mime_type: text/markdown
```

Do not invent missing content. Surface the omission after generation/import.

## Portable Agent v2 Workflow Node

The graph still uses a standard custom wrapper. Its `data` payload is:

```yaml
title: "Researcher"
type: agent
version: "2"
agent_node_kind: dify_agent
agent_binding:
  binding_type: inline_agent
  package_ref: agent_1
agent_job:
  schema_version: 1
  mode: tell_agent_what_to_do
  workflow_prompt: "Research the request and return a concise result."
  previous_node_output_refs:
    - selector: [start, task]
  declared_outputs: []
  human_contacts: []
  metadata: {}
```

Rules:

- `version` must be the string `"2"` and `agent_node_kind` must be
  `dify_agent`.
- `agent_binding.package_ref` must resolve to a top-level package. Portable
  export keeps the original binding type (`inline_agent` or `roster_agent`) and
  replaces workspace IDs with `package_ref`.
- `agent_job.schema_version` is 1.
- `agent_job` rejects unknown top-level fields. Its supported fields are
  `schema_version`, `mode`, `workflow_prompt`, `previous_node_output_refs`,
  `declared_outputs`, `human_contacts`, and `metadata`.
- `previous_node_output_refs[].selector` uses the normal Dify selector shape.
- An empty `declared_outputs` means the runtime defaults to `text`, `files`, and
  `json`. If non-empty, downstream selectors must use those declared names.
- Every declared output requires an identifier-like `name` and one of `string`,
  `number`, `object`, `array`, `boolean`, or `file` as `type`.
- The corresponding graph edge metadata still uses `sourceType: agent`.

## Human Input

```yaml
title: "Review"
type: human-input
delivery_methods:
  - id: webapp
    type: webapp
    enabled: true
form_content: "Review the generated result."
inputs:
  - type: paragraph
    output_variable_name: comment
    default:
      type: constant
      selector: []
      value: ""
user_actions:
  - id: approve
    title: "Approve"
    button_style: primary
timeout: 3
timeout_unit: day
```

Human Input rules from the backend/frontend schemas:

- `inputs` support `paragraph`, `select`, `file`, and `file-list`.
- `select` requires `option_source`; variable defaults and option sources use
  selectors with at least two string elements.
- File inputs accept `image`, `document`, `audio`, `video`, or `custom`;
  `custom` requires extensions, upload methods are `local_file`/`remote_url`,
  and `file-list.number_limits` is non-negative.
- Every `output_variable_name` must be unique and becomes a node output. Human
  Input also exposes `__action_id`, `__action_value`, and `__rendered_content`;
  `{{#$output.<name>#}}` form fields expose `<name>`.
- Every action ID must be unique, at most 20 characters, start with a letter or
  underscore, and contain only letters, numbers, and underscores.
- Action title maximum is 100 characters.
- Button styles are `primary`, `default`, `accent`, and `ghost`.
- `timeout_unit` is `hour` or `day`.
- Each normal outgoing edge uses a configured action ID as `sourceHandle`.
  Exported timeout branches use `__timeout` (the 1.16 backend adapter also
  contains the internal spelling `__timeout__`; the validator accepts both).
- Delivery methods currently include webapp, email, Slack, Teams, and Discord;
  non-webapp methods can contain workspace-specific recipient/config data.

## Dependencies

0.7.0 retains the top-level dependency types from 0.6.0:

- `marketplace` with `marketplace_plugin_unique_identifier`;
- `package` with `plugin_unique_identifier`;
- `github` with repo, version, package, and
  `github_plugin_unique_identifier`.

Dependencies must cover providers used by ordinary nodes and by nested Agent
package soul configuration. Credentials are not dependencies and must not be
embedded.

## Import And Export Behavior

- Keep `version` quoted and `kind: app`.
- Dify compares the imported semantic version with its current DSL version and
  can return warnings or confirmation requirements for older/newer files.
- Export clears workspace-specific trigger and credential values as described in
  the 0.6.0 reference, and additionally packages/sanitizes Agent definitions.
- Agent import validates each package before resolving refs. An unresolved
  top-level or workflow-node package ref is an import blocker.
- Package import can return structured warnings for omitted assets.

## Scaling Generation Safely

Dify 1.16's AI workflow generator separates responsibilities:

1. A planner chooses a graph plan.
2. Node builders create leaf-node configurations, with independent work capable
   of running in parallel.
3. Deterministic post-processing repairs IDs, handles, layout, and references.
4. Structural validation checks a single entry, terminal presence, graph cycles,
   reference integrity, and installed tools before accepting the draft.

Use the same boundary in external generation systems: let models propose intent
and node payloads, but centrally own IDs/edges/dependencies and gate every result
with deterministic validation. At scale, retry only the failed node or assembly
phase instead of regenerating the entire workflow.

## 0.7.0 Release Checklist

- Version and mode agree; Agent mode is never emitted as 0.6.0.
- Every graph runtime node is reachable from an entry.
- A normal Workflow has reachable `end`; Chatflow has reachable `answer`.
- No accidental cycles exist.
- Branch handles resolve to cases/classes/actions.
- Missing declared branch connections and duplicate reuse of one branch handle
  are behavior-risk warnings; invalid handles remain errors.
- Iteration/loop `start_node_id`, `parentId`, child membership, and container
  references resolve consistently; containers are not empty.
- Selectors resolve to known nodes and known static outputs.
- All Agent package refs resolve and package schema versions are 1.
- Plugin dependencies cover graph nodes and Agent packages.
- No credentials or private assets are embedded.
- `scripts/validate_dsl.py --target-version 0.7.0` passes before import testing.
