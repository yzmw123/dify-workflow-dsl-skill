# Dify 1.18 target

Baseline: official `1.18.0`, commit `50abea97062110044f15d0e03ccecadd9ccc87ca`.
Checked on 2026-10-30. The App DSL constant remains `0.7.0`.

Select `--dify-version 1.18`, `1.16`, or `1.15` independently of the DSL version.
Patch suffixes such as `1.18.0` select the corresponding minor-release profile;
they do not claim that every future patch has been independently tested.
Without a Dify target, DSL 0.6.0 uses the 1.15 profile and DSL 0.7.0 uses 1.18.
For an existing file targeting an older workspace, specify that workspace's
profile. Keep `--target-version` when an exact DSL version is also required.

## Agent outputs and routes

Legacy plugin-strategy Agent nodes may also use `version: "2"`. The explicit
`agent_node_kind: dify_agent` marker identifies portable Dify Agent nodes;
preserve strategy/provider fields and plugin-defined outputs on legacy nodes.

Dify 1.18 derives `text` as a system output in addition to custom outputs.
`text`, `switch`, and `_session` are reserved top-level declaration names.
The 1.16 defaults `files` and `json` are not assumed for 1.18; explicitly declare
file/structured outputs when needed. Existing 1.16 validation retains its
original output rules.

For a routed portable Agent node, keep both representations in sync:

```yaml
agent_output_routes:
  enabled: true
  routes:
    - {id: resolve, name: "The request can be answered directly.", label: Resolve}
    - {id: escalate, name: "The request needs a specialist.", label: Escalate}
agent_job:
  schema_version: 1
  workflow_prompt: "Handle the request and choose the appropriate route."
  declared_outputs: []
  output_routes:
    enabled: true
    routes:
      - {id: resolve, name: "The request can be answered directly.", label: Resolve}
      - {id: escalate, name: "The request needs a specialist.", label: Escalate}
```

Enabled routes require at least two unique IDs and nonblank `name` selection
conditions. `label` is optional display text. IDs cannot be `source`, `target`,
or `fail-branch`. Connect outgoing edges using route IDs as `sourceHandle`.
The read-only `switch` output contains the chosen ID. `fail-branch` is valid
only when the node's `error_strategy` is `fail-branch`. Node-level
`default-value` handling is incompatible with enabled routes. With routing
disabled, the success handle remains `source`.

Use `agent_task` for the graph's task text and `agent_job.workflow_prompt` for
the portable bound job; keep the intended instruction aligned. The local gate
checks references and branch coverage; the source gate checks official models
and route execution completeness. Neither invokes an Agent/model.

See [Agent route example](../examples/dify-1.18.0/02-agent-routes.yml).

## Workspace skills and knowledge

Agent packages accept `workspace_skills`, a list of bindings with `name`
(1–64 characters), `display_name`, `description`, and required non-negative
integer `priority`. A binding does not embed skill bytes or guarantee that the
destination workspace has a matching skill.

`soul.knowledge` accepts classic `sets` and KnowledgeFS `spaces`. A space has
`id`, `control_space_id` (36-character control-plane UUID), `name` (alias),
optional `description`, and boolean `is_missing`. Up to ten spaces are allowed.
IDs, aliases, and control-space IDs must be unique; aliases cannot shadow
another binding's ID. Avoid collisions with classic sets. Preserve unresolved
bindings as missing and reconnect them in the target workspace.

For missing `config_files` or `config_skills`, Dify 1.18 accepts the early-export
placeholder `file_id: null` when `is_missing: true`. New YAML should use an empty
string for the ID. A present asset still requires a nonblank ID.

KnowledgeFS retrieval uses node type `knowledge-retrieval-v2`, not version 2
of the classic `knowledge-retrieval` type. It requires 1–10 `control_space_ids`
and a text or attachment query selector. `top_n` is 1–100 (default 10),
`score_threshold` is 0–1 or null, and `mode` is `deep`, `fast`, `research`, or null.
Its output is `result`. Copy advanced metadata/reranking configuration from the
target workspace and run the official source gate; the local checker validates
the core fields and object shapes, not the complete retrieval contract.

KnowledgeFS is opt-in and requires its service/configuration. The example UUIDs
in this repository are synthetic placeholders, not usable workspace identities.

## YAML, .ifpkg, and Site settings

Dify 1.18 exports `.ifpkg` by default and can still explicitly export YAML.
Packages can carry supported inline Agents, Skills, and files; imports recreate
resources and remap their references. Standalone YAML omits resource payloads
and sanitizes credentials. Do not change a YAML extension to `.ifpkg`.

This skill's local validator accepts YAML, not binary package archives. Use
Dify's own import path for `.ifpkg`; obtain an explicit YAML export for local
review. Do not infer package completeness from a YAML validation pass.

Top-level `site` carries presentation settings such as title, description,
language, theme, and workflow-step visibility. Deployment identity and access
policy (site code, custom domain, token strategy, status) are excluded. The
source gate validates the exact Site model, including supported languages.

## Official difyctl integration

The 1.18 CLI discovers online app operations from the server's OpenAPI catalog,
including Workflow/Chatflow creation, DSL import/export, settings, publishing,
and restoration. Use the matching CLI and its current `help` output. Install
its bundled agent skill with `difyctl install skills <dir>` when the task needs
online app management. Keep this skill's local YAML authoring/validation role;
do not add server credentials or execute publishing as part of static validation.

## Source authorities

- [DSL constant](https://github.com/langgenius/dify/blob/1.18.0/api/constants/dsl_version.py)
- [Agent package models](https://github.com/langgenius/dify/blob/1.18.0/api/services/agent/dsl_entities.py)
- [Agent configuration, outputs, and routes](https://github.com/langgenius/dify/blob/1.18.0/api/models/agent_config_entities.py)
- [Agent node runtime](https://github.com/langgenius/dify/blob/1.18.0/api/core/workflow/nodes/agent_v2/agent_node.py)
- [Knowledge Retrieval v2](https://github.com/langgenius/dify/blob/1.18.0/api/services/knowledge_fs/knowledge_retrieval_v2/entities.py)
- [Site model](https://github.com/langgenius/dify/blob/1.18.0/api/services/entities/site_dsl.py)
- [1.18 release and difyctl](https://github.com/langgenius/dify/releases/tag/1.18.0)
