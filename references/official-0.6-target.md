# Official DSL 0.6.0 Compatibility Target

Use this reference when the target is Dify 1.15.x or an existing DSL 0.6.0 app.
For new Dify 1.16.x generation, use `official-0.7-target.md` instead.

## Contents

- Sources checked
- Target rule
- Import and version compatibility
- Export shape
- Export sanitization
- Dependency types and sources
- Official node type set
- Common node and edge metadata
- Input variable types
- Public sample availability

## Sources Checked

- Dify 1.15.0 DSL constant:
  https://github.com/langgenius/dify/blob/1.15.0/api/constants/dsl_version.py
- Dify app import/export service:
  https://github.com/langgenius/dify/blob/1.15.0/api/services/app_dsl_service.py
- Dify plugin dependency analysis:
  https://github.com/langgenius/dify/blob/1.15.0/api/services/plugin/dependencies_analysis.py
- Dify plugin dependency entity:
  https://github.com/langgenius/dify/blob/1.15.0/api/core/plugin/entities/plugin.py
- Dify workflow frontend types:
  https://github.com/langgenius/dify/blob/1.15.0/web/app/components/workflow/types.ts
- Dify workflow common-node registry:
  https://github.com/langgenius/dify/blob/1.15.0/web/app/components/workflow/constants/node.ts

## Target Rule

- Dify 1.15.x-compatible app DSL should use `version: "0.6.0"`.
- Keep `version` quoted. Dify import expects a string and rejects non-string
  values.
- Use `kind: app`.
- Prefer graph-based `workflow` and `advanced-chat` modes for new work.
- Use public DSLs as compatibility and workflow-design evidence only. Most
  sampled public repositories are legacy exports; a later scan found a small
  public `0.6.0` sample, but official source remains the target authority.

## Import And Version Compatibility

Dify compares imported DSL version with the server's current version:

- Same version or same minor/micro-compatible older version: normal import.
- Older minor version: import can complete with warnings.
- Older major version or newer-than-current version: import may require user
  confirmation or migration.
- Missing `version` is filled as old `0.1.0` by import logic, but generated DSL
  should never rely on that fallback.

## Export Shape

Official export builds this top-level structure:

```yaml
version: "0.6.0"
kind: app
app:
  name: "App name"
  mode: advanced-chat
  icon: "🤖"
  icon_type: emoji
  icon_background: "#FFEAD5"
  description: ""
  use_icon_as_answer_icon: false
dependencies: []
workflow:
  graph:
    nodes: []
    edges: []
```

For `advanced-chat` and `workflow`, export appends `workflow`. For `chat`,
`agent-chat`, and `completion`, export appends top-level `model_config`.

## Export Sanitization

Official export removes or resets workspace-specific fields:

- Tool node `credential_id` is removed unless secrets are explicitly included.
- Agent tool `credential_id` is removed unless secrets are explicitly included.
- Trigger schedule config is reset to its default export form.
- Trigger webhook `webhook_url` and `webhook_debug_url` are cleared.
- Trigger plugin `subscription_id` is cleared.
- Knowledge retrieval `dataset_ids` may be encrypted on export and decrypted on
  import depending on Dify server configuration.

Do not hardcode real credentials, webhook URLs, subscription IDs, DB passwords,
or private dataset IDs in public templates.

## Dependency Types

Official dependency entries can be `marketplace`, `package`, or `github`.

Marketplace:

```yaml
- current_identifier: null
  type: marketplace
  value:
    marketplace_plugin_unique_identifier: langgenius/openai:0.0.23@...
    version: null
```

Package/private plugin:

```yaml
- current_identifier: null
  type: package
  value:
    plugin_unique_identifier: author/plugin:0.0.1@...
    version: null
```

GitHub-installed plugin:

```yaml
- current_identifier: null
  type: github
  value:
    repo: author/plugin-repo
    version: 0.0.1
    package: plugin-package-name
    github_plugin_unique_identifier: author/plugin:0.0.1@...
```

Remote plugins are not exportable by official Dify export logic.

## Dependency Sources

Dify extracts dependencies from:

- LLM nodes: `model.provider`
- Question classifier nodes: `model.provider`
- Parameter extractor nodes: `model.provider`
- Tool nodes: `provider_id`
- Knowledge retrieval nodes: reranking model, weighted-score embedding provider,
  or single retrieval model provider
- Model config apps: main model, dataset reranking model, and agent tools

Agent node strategy/tool dependencies can still be more complex than this list in
practice. Preserve exported `dependencies` whenever available.

## Official Node Type Set

The Dify 1.15 workflow frontend type enum includes:

```text
start, end, answer, llm, knowledge-retrieval, question-classifier, if-else,
code, template-transform, http-request, variable-assigner,
variable-aggregator, tool, parameter-extractor, iteration,
document-extractor, list-operator, iteration-start, assigner, agent, loop,
loop-start, loop-end, human-input, datasource, datasource-empty,
knowledge-index, trigger-schedule, trigger-webhook, trigger-plugin
```

The common node registry currently exposes common authoring defaults for:

```text
llm, knowledge-retrieval, agent, question-classifier, if-else, iteration,
iteration-start, loop, loop-start, loop-end, code, template-transform,
variable-aggregator, document-extractor, assigner, parameter-extractor,
http-request, list-operator, tool, human-input
```

Trigger, datasource, and knowledge-index nodes exist but are more
deployment-sensitive. Prefer copying a fresh export from the target Dify
workspace for production use.

## Common Node And Edge Metadata

Official common node data can include:

```text
isInIteration, iteration_id, isInLoop, loop_id, error_strategy,
retry_config, default_value, credential_id, subscription_id, provider_id
```

Official edge data can include:

```text
isInIteration, iteration_id, isInLoop, loop_id, sourceType, targetType
```

For new graph DSL, include `sourceType` and `targetType` on every edge and keep
them synchronized with each endpoint node's `data.type`.

## Input Variable Types

Current frontend input variable types include:

```text
text-input, paragraph, select, number, url, files, json, json_object,
contexts, iterator, file, file-list, loop, checkbox
```

Use these exact strings in start variables, human-input forms, and node input
schemas when supported by the node.

## Public Sample Availability

Version scan on 2026-05-07:

- `BannyLon/DifyAIA`: 38 parsed app DSL, `0.6.0`: 0
- `svcvit/Awesome-Dify-Workflow`: 45 parsed app DSL, `0.6.0`: 0
- `wwwzhouhui/dify-for-dsl`: 89 parsed app DSL, `0.6.0`: 0
- Official Dify workflow fixtures checked locally: 24 parsed app DSL,
  versions `0.3.1` to `0.5.0`, `0.6.0`: 0

Additional scan on 2026-05-11:

- `g-krishna0/dify-export-test`: 87 parsed app DSL, `0.6.0`: 0
- `Petrus-Han/dify-usecase-playground`: 3 parsed app DSL, `0.6.0`: 1

This historical sample evidence remains useful for 0.6.0 compatibility. The
skill now defaults new Dify 1.16.x files to 0.7.0 while retaining these rules and
validator coverage for existing 0.6.0 apps.
