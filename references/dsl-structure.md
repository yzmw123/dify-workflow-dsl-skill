# Dify DSL Structure

This reference covers app-level structure, graph wiring, variables, dependencies,
and import/export compatibility.

## Contents

- Version baselines
- Top-level YAML
- Mode rules
- Dependencies
- Official node type set
- Node and edge wrappers
- Variable references
- Workflow variables
- Import-sensitive details
- Agent App and legacy model-config apps

## Version Baselines

- Dify 1.16.0 declares `CURRENT_APP_DSL_VERSION = "0.7.0"`; Dify 1.15.0
  declares `"0.6.0"`.
- Import expects `version` to be a string.
- New Dify 1.16.x DSL should target `version: "0.7.0"`. Use `"0.6.0"` for
  Dify 1.15.x compatibility, and preserve supported versions during review unless
  migration was requested.
- Dify can backfill latest dependencies for very old imports (`<=0.1.5`) when
  `dependencies` is absent. For new DSL, explicit dependencies are safer for
  cross-workspace import.
- Exported workflow graphs mirror ReactFlow: each node has an outer wrapper and a
  `data` object; edges connect `source`/`target` node IDs and handles.

Primary sources used for this skill:

- Dify 1.16.0 DSL version constant:
  https://github.com/langgenius/dify/blob/1.16.0/api/constants/dsl_version.py
- Dify app DSL import/export service:
  https://github.com/langgenius/dify/blob/1.16.0/api/services/app_dsl_service.py
- Dify dependency analysis:
  https://github.com/langgenius/dify/blob/1.16.0/api/services/plugin/dependencies_analysis.py
- Dify workflow frontend types:
  https://github.com/langgenius/dify/blob/1.16.0/web/app/components/workflow/types.ts
- Sample workflow repositories:
  https://github.com/BannyLon/DifyAIA,
  https://github.com/svcvit/Awesome-Dify-Workflow,
  https://github.com/wwwzhouhui/dify-for-dsl,
  https://github.com/g-krishna0/dify-export-test,
  https://github.com/Petrus-Han/dify-usecase-playground

## Top-Level YAML

```yaml
app:
  name: "App name"
  description: "What this workflow does"
  icon: "🤖"
  icon_type: emoji
  icon_background: "#FFEAD5"
  mode: advanced-chat       # workflow | advanced-chat | chat | completion | agent-chat | agent (0.7.0)
  use_icon_as_answer_icon: false
kind: app
version: "0.7.0"
dependencies: []
workflow:
  conversation_variables: []
  environment_variables: []
  features:
    file_upload:
      enabled: false
      image:
        enabled: false
        number_limits: 3
        transfer_methods: [local_file, remote_url]
      allowed_file_extensions: []
      allowed_file_types: []
      allowed_file_upload_methods: [local_file, remote_url]
      number_limits: 3
    opening_statement: ""
    retriever_resource:
      enabled: true
    sensitive_word_avoidance:
      enabled: false
    speech_to_text:
      enabled: false
    suggested_questions: []
    suggested_questions_after_answer:
      enabled: false
    text_to_speech:
      enabled: false
      language: ""
      voice: ""
  graph:
    nodes: []
    edges: []
    viewport:
      x: 0
      y: 0
      zoom: 0.8
```

## Mode Rules

| mode | Typical use | Input source | Terminal node |
| --- | --- | --- | --- |
| `workflow` | one-shot, batch, triggered, or integration automation | start variables or trigger payload | `end`; side-effect trigger flows may finish at a tool |
| `advanced-chat` | Chatflow with multi-turn chat | `sys.query`, `sys.files`, conversation variables | `answer` |
| `chat` | legacy/simple chat app | model config | model config |
| `completion` | legacy completion app | model config/start inputs | model config |
| `agent-chat` | legacy agent chat app | model config | model config |
| `agent` | portable top-level Agent App (0.7.0) | Agent package/soul | Agent runtime |

For new graph DSL, prefer `workflow` or `advanced-chat`. Default to
`workflow` unless the user needs Chatflow behavior such as multi-turn memory,
`sys.query`, `sys.files`, or answer streaming. Use `agent` only with the 0.7.0
top-level `agent` and `agent_packages` structure in `official-0.7-target.md`.

## Dependencies

Official Dify app DSL dependencies can be `marketplace`, `package`, or `github`.
Remote plugins are not exportable by official Dify export logic.

Marketplace plugin dependency:

```yaml
dependencies:
  - current_identifier: null
    type: marketplace
    value:
      marketplace_plugin_unique_identifier: langgenius/tongyi:0.1.36@73e3e28eca163b96da65ef9eab8633f9e7257213ff0d2f2bed93b28b552d2cda
      version: null
```

Package/private plugin dependency:

```yaml
dependencies:
  - current_identifier: null
    type: package
    value:
      plugin_unique_identifier: wwwzhouhui/nano_banana2_text2image:0.0.1@4069e9bfe87735fcd0276e08b84eefdd87fb05e82aa5228ef44df17390a8239b
      version: null
```

GitHub-installed plugin dependency:

```yaml
dependencies:
  - current_identifier: null
    type: github
    value:
      repo: author/plugin-repo
      version: 0.0.1
      package: plugin-package-name
      github_plugin_unique_identifier: author/plugin:0.0.1@4069e9bfe87735fcd0276e08b84eefdd87fb05e82aa5228ef44df17390a8239b
```

Use the exact `marketplace_plugin_unique_identifier` or `plugin_unique_identifier`
exported by the source Dify workspace when possible. If hand-authoring a public
template, keep the plugin name and version realistic, but tell users they may need
to reinstall or reselect the plugin in Dify after import.

Common dependency sources:

- LLM providers: `model.provider`
- Tool nodes: `provider_id` for dependency analysis, plus
  `plugin_unique_identifier` when exported in the node
- Agent strategies and built-in tools inside agent nodes
- Knowledge retrieval/indexing and datasource nodes
- Providers/tools nested inside DSL 0.7.0 Agent packages

Official export dependency extraction currently reads model providers from LLM,
question-classifier, parameter-extractor, knowledge-retrieval rerank/embedding
config, tool `provider_id`, and model-config apps. Preserve exported
`dependencies` when available because complex agent/plugin arrangements can carry
more detail than a hand-written dependency list.

## Official Node Type Set

Dify 1.16 workflow node types include:

```text
start, end, answer, llm, knowledge-retrieval, question-classifier, if-else,
code, template-transform, http-request, variable-assigner,
variable-aggregator, tool, parameter-extractor, iteration,
document-extractor, list-operator, iteration-start, assigner, agent, loop,
loop-start, loop-end, human-input, datasource, datasource-empty,
knowledge-index, trigger-schedule, trigger-webhook, trigger-plugin
```

Current input variable types include:

```text
text-input, paragraph, select, number, url, files, json, json_object,
contexts, iterator, file, file-list, loop, checkbox
```

## Node Wrapper

```yaml
- data:
    title: "Readable title"
    type: llm
    selected: false
  id: "1770000000000"
  position:
    x: 334
    y: 300
  positionAbsolute:
    x: 334
    y: 300
  selected: false
  sourcePosition: right
  targetPosition: left
  type: custom
  width: 243
  height: 89
```

Use string IDs. Dify exports numeric-looking IDs as strings; keep them quoted.

Canvas note nodes are non-executable annotations:

```yaml
- data:
    author: ""
    desc: "Implementation note"
    height: 120
    selected: false
    showAuthor: false
    text: "Explain a branch or TODO here."
    theme: blue
    title: ""
    type: ""
    width: 260
  id: "note-1"
  position: { x: 600, y: 120 }
  positionAbsolute: { x: 600, y: 120 }
  selected: false
  type: custom-note
```

Do not treat missing/empty `data.type` as an error when wrapper `type` is
`custom-note`.

## Edge Wrapper

```yaml
- data:
    isInLoop: false
    isInIteration: false
    sourceType: start
    targetType: llm
  id: 1770000000000-source-1770000000001-target
  selected: false
  source: "1770000000000"
  sourceHandle: source
  target: "1770000000001"
  targetHandle: target
  type: custom
  zIndex: 0
```

Handle conventions:

- Linear edge: `sourceHandle: source`, `targetHandle: target`
- `if-else`: source handle is the case ID (`"true"`, `"false"`, or UUID)
- `question-classifier`: source handle is the class ID (`"1"`, `"2"`, ...)
- `human-input`: source handle is a configured `user_actions[].id`
- Iteration/loop internals: include `isInIteration` or `isInLoop` and the parent
  node ID fields when exported by Dify

## Variable References

Prompt interpolation:

```text
{{#node_id.field#}}
{{#sys.query#}}
{{#sys.files#}}
{{#sys.user_id#}}
{{#conversation.Memory#}}
{{#env.API_KEY#}}
```

Selector fields:

```yaml
value_selector: ["1770000000001", text]
variable_selector: ["sys", query]
query: ["1770000000001", text]
```

Some Dify 1.16 frontend node configs encode Chatflow system variables as
`[startNodeId, "sys.query"]`; the equivalent canonical system selector is
`["sys", "query"]`. Some older exports use one-element dotted arrays such as
`["sys.query"]`. Prefer the canonical two-element selector for new files unless
matching an existing export.

## Workflow Variables

Conversation variables are for `advanced-chat` memory/state:

```yaml
conversation_variables:
  - description: ""
    id: 7a9ac6e3-0000-4000-9000-000000000001
    name: Memory
    selector: [conversation, Memory]
    value: ""
    value_type: string
```

Older public exports sometimes omit `selector` on conversation variables. For new
DSL, include it; when reviewing old DSL, absence of `selector` alone is not
necessarily import-breaking.

Environment variables are read-only workflow constants:

```yaml
environment_variables:
  - description: "Base URL"
    id: 7a9ac6e3-0000-4000-9000-000000000002
    name: FILES_URL
    selector: [env, FILES_URL]
    value: "https://example.local/"
    value_type: string
```

Supported value types commonly include `string`, `number`, `boolean`, `object`,
`array[string]`, `array[number]`, `array[object]`, `array[file]`, and `file`.

## Import-Sensitive Details

- Quote `version`, node IDs, branch handles, and large numeric-looking values.
  Some real DSLs leave `version: 0.3.0` unquoted and it often parses as a string,
  but quoting avoids YAML parser differences.
- Keep `sourceType`/`targetType` synchronized with each endpoint node's `data.type`.
- Do not omit final nodes: a normal `workflow` needs `end`; `advanced-chat` needs
  at least one reachable `answer`. A trigger-based side-effect workflow can omit
  `end` intentionally, but then it returns no normal outputs.
- `agent-chat`, `chat`, and `completion` may use top-level `model_config` instead
  of `workflow.graph`; this is common in legacy/public exports.
- Do not hardcode real plugin credentials. Exported plugin authorization generally
  lives in Dify, not in DSL.
- Tool nodes generated from real exports often include `paramSchemas` and `params`.
  They are verbose but improve UI fidelity. When hand-authoring, keep required
  tool identity and parameters, and prefer copying `paramSchemas` from an export
  if the target Dify import complains.

## DSL 0.7.0 Agent App

An Agent App does not use `workflow.graph` or legacy `model_config`. It resolves
a portable Agent package:

```yaml
version: "0.7.0"
kind: app
app: {name: "Agent", mode: agent}
agent: {package_ref: agent_1}
agent_packages:
  agent_1:
    schema_version: 1
    metadata: {name: "Agent", description: "", role: ""}
    soul: {schema_version: 1}
    omitted_assets: []
dependencies: []
```

See `official-0.7-target.md` for package sanitization, omitted assets, and Agent
v2 workflow nodes.

## Agent-Chat / Legacy Model Config Apps

Some public DSLs, especially `agent-chat`, do not have a workflow graph. They use
top-level `model_config`:

```yaml
app:
  mode: agent-chat
kind: app
version: "0.3.0"
model_config:
  agent_mode:
    enabled: true
    max_iteration: 10
    strategy: react
    tools:
      - enabled: true
        provider_id: pdftranslate-mcp-server
        provider_name: pdftranslate-mcp-server
        provider_type: mcp
        tool_label: translate_pdf
        tool_name: translate_pdf
        tool_parameters:
          file_input: ""
          filename: ""
  model:
    provider: langgenius/siliconflow/siliconflow
    name: deepseek-ai/DeepSeek-V3
    mode: chat
  user_input_form: []
```

For new apps, prefer graph-based `workflow` or `advanced-chat` unless the user
explicitly asks for legacy/simple app modes. When reviewing existing DSL, do not
fail an `agent-chat` app just because `workflow.graph` is absent.
