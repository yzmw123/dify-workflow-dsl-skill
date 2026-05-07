---
name: dify-workflow-dsl
description: >
  Create, modify, review, and debug Dify Workflow/Chatflow DSL YAML files that can
  be imported into Dify. Use for Dify app DSL, workflow YAML, advanced-chat YAML,
  graph nodes/edges, variables, tool nodes, plugin dependencies, database read/write
  tools, and import/export compatibility questions.
---

# Dify Workflow DSL

Use this skill to produce import-ready Dify DSL YAML. Dify calls the exported
workflow file a DSL; it is a YAML app definition with app metadata, dependencies,
workflow variables/features, and a ReactFlow-like graph of nodes and edges.

## Core Workflow

1. Clarify only import-blocking requirements: app mode (`workflow` or `advanced-chat`),
   required inputs, model/provider, installed plugins, knowledge bases, secrets,
   and expected outputs.
2. Choose the DSL version. For new DSL, target official Dify app DSL
   `version: "0.6.0"` unless the user explicitly asks for old-version
   compatibility. Always write `version` as a YAML string.
3. Sketch the graph before writing YAML: start/input, transform/reasoning nodes,
   tools, branches/loops, final `end` or `answer`.
4. Use stable string node IDs and connect every edge with matching `sourceType`,
   `targetType`, `sourceHandle`, and `targetHandle`.
5. Add `dependencies` for every plugin-backed LLM provider, tool, agent, knowledge
   feature, and model config. Support marketplace, package, and GitHub dependency
   entries; use exact exported plugin identifiers when available.
6. For any plugin/tool not covered by existing examples, follow
   `references/plugin-marketplace-tools.md`: prefer a minimal exported DSL from
   the user's Dify workspace, then plugin source/package metadata, then marketplace
   pages. Be explicit about reliability when exact tool schemas are unavailable.
7. Validate locally with `python3 scripts/validate_dsl.py <file.yml>` before giving
   the user the YAML path.

## Reference Map

Load only the relevant reference files:

- `references/official-0.6-target.md` for official current-version rules from
  Dify source: DSL version, import/export behavior, dependency types, current node
  enum, trigger/datasource cautions, and public sample availability.
- `references/dsl-structure.md` for top-level YAML, variables, dependencies,
  edges, handles, and import/export rules.
- `references/node-schemas.md` for node-specific schemas and examples.
- `references/database-tools.md` for PostgreSQL/SQL read-write tool nodes,
  including `spance/db_client_node` and `hjlarry/database` patterns from the
  user's exported DSLs.
- `references/plugin-marketplace-tools.md` for defining new plugin tool nodes from
  Dify Marketplace, GitHub plugin repos, `.difypkg` packages, or minimal exports.
- `references/real-world-yml-study.md` for observations from 172 parsed public
  Dify app DSL files and 39 detailed representative legacy samples. These samples
  are real-world compatibility evidence, not the target version authority.
- `references/complete-examples.md` for full importable examples and graph layouts.

## Required Decisions

- **Mode**: use `workflow` for one-shot runs with `end`; use `advanced-chat` for
  Chatflow, `sys.query`, `sys.files`, memory, and `answer` nodes.
- **Inputs**: in `workflow`, define start `variables`; in `advanced-chat`, keep
  start variables empty unless the app needs explicit form inputs.
- **Secrets**: do not hardcode real API keys, DB passwords, or webhook secrets.
  Prefer Dify plugin authorization, `env` variables, or clear placeholders.
- **Database access**: prefer parameterized tool calls (`$arg0`, `$arg1`, ...)
  over interpolated SQL. For LLM-generated SQL, restrict to SELECT unless the
  user explicitly asks for writes and accepts the risk.
- **Model/provider**: keep provider names exactly as Dify exports them, for example
  `langgenius/tongyi/tongyi`, `openai`, or a marketplace provider path.
- **New plugin tools**: do not promise import-and-run reliability from a tool name
  alone. Ask for a minimal exported DSL or plugin source/package when exact
  `provider_id`, `tool_name`, parameters, and authorization schema are unknown.

## Authoring Rules

- For newly generated DSL, use `version: "0.6.0"` and top-level `kind: app`.
- `workflow.graph.nodes` and `workflow.graph.edges` must both exist.
- Node wrapper `type` is normally `custom`; `data.type` is the real node kind.
- Every node `id` should be a string. Do not reuse IDs.
- Edges must reference existing node IDs.
- Branch edges from `if-else` use source handles from case IDs, commonly `"true"`,
  `"false"`, or a UUID custom case ID.
- Question classifier source handles use class IDs such as `"1"`, `"2"`.
- Iteration/loop internals need `isInIteration`/`isInLoop`, parent IDs, and start
  helper nodes when exported by Dify.
- `value_selector` and `variable_selector` are arrays, for example
  `["node_id", "text"]`; prompt interpolation is `{{#node_id.field#}}`.
- Code nodes must define the runtime entrypoint: Python uses `def main(...)`,
  JavaScript/TypeScript uses `function main(...)` or an equivalent `main`
  function. Return keys must match `outputs`.
- Tool nodes must include `provider_id`, `provider_name`, `provider_type`,
  `tool_name`, `tool_label`, and `tool_parameters`. `plugin_id`,
  `plugin_unique_identifier`, and `tool_node_version` are common but not universal;
  preserve them when copied from an export.
- `provider_type` may be `builtin`, `api`, `workflow`, or `mcp`.
- Dependencies may use `type: marketplace` with `marketplace_plugin_unique_identifier`,
  `type: package` with `plugin_unique_identifier`, or `type: github` with
  `github_plugin_unique_identifier` plus repo/package metadata.
- `custom-note` nodes are valid canvas annotations and may have empty `data.type`.
- `agent-chat`, `chat`, and `completion` apps may be top-level `model_config`
  apps with no `workflow.graph`; do not force graph rules onto them when reviewing
  legacy exports.
- For public examples, replace tenant-specific icon URLs and credentials with
  placeholders unless they are harmless exported metadata.

## Validation Checklist

Before finalizing a DSL:

- YAML parses cleanly.
- `version` is a string and `app.mode` matches terminal node type.
- Dependencies cover all plugin-backed nodes.
- All graph edges resolve to existing nodes and matching data types.
- Start variables, conversation variables, and environment variables have unique
  names. Include selectors for new variables; tolerate missing conversation
  selectors when reviewing older exports.
- Every LLM has a model and prompt template.
- Every tool has required provider/tool fields and parameter values.
- New or rare plugin tools are backed by an exported node, plugin package/source,
  or clearly labeled as a best-effort draft that still needs Dify import testing.
- SQL has no trailing comma before `)` and uses bound parameters for dynamic values.
- The final answer tells the user which file was written and whether validation
  passed.

## Useful Commands

```bash
python3 scripts/validate_dsl.py path/to/workflow.yml
python3 scripts/validate_dsl.py examples/*.yml
```

If the user only asks for a review, report import risks and behavioral bugs first,
with file/line references when possible. If the user asks to create or modify a
workflow, write or patch the YAML directly and validate it.
