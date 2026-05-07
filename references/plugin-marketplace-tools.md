# Plugin Marketplace Tool Nodes

Use this reference when a workflow needs a Dify tool that is not already covered
by local exported examples.

## Contents

- Reliability ladder
- Preferred workflow for new tools
- Tool node identity template
- `paramSchemas` guidance
- Authorization and secrets
- When to refuse a guarantee

## Reliability Ladder

| Evidence available | Reliability | How to proceed |
| --- | --- | --- |
| Minimal exported DSL from the user's Dify workspace | Highest | Copy the node envelope, dependency, `paramSchemas`, `tool_configurations`, and `tool_parameters`; then adapt values only. |
| Plugin source repo or `.difypkg` package | High | Read `manifest.yaml`, provider YAML, tool YAML, and Python implementation; infer the DSL node and warn that import should still be tested. |
| Official marketplace page only | Medium | Use visible plugin/version/tool info if available, but mark the node as a candidate because parameter schema and authorization details may be incomplete. |
| Tool name only | Low | Do not claim it will work. Ask for an export, source/package, or screenshot. Generate only a placeholder/draft if the user explicitly accepts the risk. |

## Preferred Workflow For New Tools

1. Ask for a minimal export when possible: create a blank Dify workflow, add the
   target tool node, configure authorization and one sample parameter, export DSL.
2. Extract these fields from the export:
   `dependencies`, `provider_id`, `provider_name`, `provider_type`, `plugin_id`,
   `plugin_unique_identifier`, `tool_name`, `tool_label`, `tool_description`,
   `tool_node_version`, `paramSchemas`, `params`, `tool_configurations`, and
   `tool_parameters`.
3. Keep the copied identity fields unchanged. Only change parameter `value` fields,
   node IDs, titles, and graph positions.
4. For plugin source/package inference, map schema fields as follows:
   - plugin manifest/package identity -> `plugin_id` and dependency entry
   - provider identity -> `provider_id` and `provider_name`
   - tool YAML name -> `tool_name`
   - tool labels/descriptions -> `tool_label` and `tool_description`
   - tool parameters with `form: llm` -> `tool_parameters`
   - tool parameters with `form: form` -> `tool_configurations`
5. After generating the DSL, run `scripts/validate_dsl.py`. Then tell the user it
   still needs an import/run test in Dify if the node was not copied from an export.

## Tool Node Identity Template

```yaml
title: "Tool title"
type: tool
is_team_authorization: true
provider_id: author/plugin/provider
provider_name: author/plugin/provider
provider_type: builtin
plugin_id: author/plugin
plugin_unique_identifier: author/plugin:0.0.1@sha256-or-marketplace-id
tool_name: tool_name_from_plugin
tool_label: "Human label"
tool_description: "What this tool does."
tool_node_version: "2"
tool_configurations: {}
tool_parameters:
  query:
    type: mixed
    value: "{{#sys.query#}}"
selected: false
```

Do not invent `plugin_unique_identifier` for a production DSL. If it is unknown,
either obtain an export/source or label the workflow as a best-effort draft.

Real exports may omit `plugin_id`, `plugin_unique_identifier`, and
`tool_node_version` inside the node. They may still be valid if the top-level
dependency or the target workspace/tool authorization supplies the missing
identity. Preserve export shape instead of normalizing everything into one schema.

Dependency entries may be marketplace, package, or GitHub based:

```yaml
- current_identifier: null
  type: marketplace
  value:
    marketplace_plugin_unique_identifier: langgenius/openai:0.0.23@...
    version: null

- current_identifier: null
  type: package
  value:
    plugin_unique_identifier: author/private_plugin:0.0.1@...
    version: null

- current_identifier: null
  type: github
  value:
    repo: author/plugin-repo
    version: 0.0.1
    package: plugin-package-name
    github_plugin_unique_identifier: author/plugin:0.0.1@...
```

Official Dify export refuses remote plugins. If the target workflow depends on a
remote plugin, ask the user to replace it with marketplace, package, or GitHub
installation before expecting portable DSL export/import.

## `paramSchemas` Guidance

Dify exports many tool nodes with a verbose `paramSchemas` list and a `params`
mapping. These fields preserve the tool editor UI and make imports more faithful.

If a copied export includes them, keep them. If hand-authoring from source:

```yaml
paramSchemas:
  - name: query
    type: string
    required: true
    form: llm
    label:
      en_US: Query
      zh_Hans: 查询
    human_description:
      en_US: The query to execute.
      zh_Hans: 要执行的查询。
    llm_description: The query to execute.
    options: []
    default: null
    placeholder: null
    min: null
    max: null
    precision: null
    scope: null
    template: null
params:
  query: ""
```

For many tools, Dify can still import without `paramSchemas`, but copying or
reconstructing them reduces UI and compatibility surprises.

## Authorization And Secrets

- Marketplace plugins often require user/team authorization. `is_team_authorization`
  in DSL is not a credential.
- `provider_type` can be `builtin`, `api`, `workflow`, or `mcp`; MCP and workflow
  tools often do not map cleanly to marketplace dependencies.
- Do not hardcode access tokens, app secrets, DB passwords, or private webhook
  tokens in public DSL.
- Prefer Dify plugin authorization, environment variables, or placeholder values.
- If a tool can accept an override credential parameter such as `api_key` or
  `db_uri`, set it from `{{#env.NAME#}}`.

## When To Refuse A Guarantee

Say clearly that a tool node cannot be guaranteed import-ready when:

- The plugin/version is unknown.
- The exact `provider_id` or `tool_name` is unknown.
- Required parameter names or `form` types are unknown.
- The plugin requires authorization not represented in DSL.
- The marketplace page does not expose enough schema detail.

In those cases, provide a draft plus a short test plan:

1. Import the DSL into a Dify test workspace.
2. Re-select or authorize the plugin if Dify prompts.
3. Open the tool node and confirm all required fields are mapped.
4. Run a minimal test input and inspect the tool output fields.
5. Update downstream selectors (`text`, `data`, `result`, `json`, `files`,
   `output`) to match the actual output.
