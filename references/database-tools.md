# Database Tool Nodes

This reference distills database read/write patterns from user-provided Dify
exports. The important takeaway is the tool-node envelope plus safe SQL parameter
binding.

## Contents

- Two useful plugin patterns
- `spance/db_client_node` insert and read templates
- Duplicate check pattern
- `hjlarry/database` SQL execute template
- NL2SQL retrieval pattern
- SQL safety checklist

## Two Useful Plugin Patterns

### `spance/db_client_node`

Use when Dify has configured a named PostgreSQL client tool such as
`postgres_node_5` or `postgres_node_10`.

- Plugin dependency: `spance/db_client_node:0.1.47@...`
- Provider: `spance/db_client_node/db_client_node`
- Tool names: `postgres_node_5`, `postgres_node_10`
- Dynamic values are passed as `arg0`...`arg4` or `arg0`...`arg9`
- SQL placeholders are `$arg0`, `$arg1`, ...
- The DB connection is handled by the Dify tool authorization/config, not by YAML

### `hjlarry/database`

Use for a general SQL execute tool where the SQL comes from a previous node.

- Plugin dependency: `hjlarry/database:0.0.6@...`
- Provider: `hjlarry/database/database`
- Tool name: `sql_execute`
- Parameters: `query`, optional `db_uri`
- Configurations: `format` (`json`, `csv`, `yaml`, `md`, `xlsx`, `html`),
  optional `config_options`
- Good for SELECT after an LLM/parameter-extractor chooses a query

## `spance/db_client_node` Insert Template

This is the corrected write pattern for parsed document records. Avoid the
trailing comma after the final column name.

```yaml
title: "把文档内容插入数据库"
type: tool
is_team_authorization: true
provider_id: spance/db_client_node/db_client_node
provider_name: spance/db_client_node/db_client_node
provider_type: builtin
plugin_id: spance/db_client_node
plugin_unique_identifier: spance/db_client_node:0.1.47@60965f21262129b75b2e01543190ab65021b75b55441532f77f88fcd7b71095d
tool_name: postgres_node_10
tool_label: "PostgreSQL 客户端(10)"
tool_description: "读写PostgreSQL客户端，最多10个参数。"
tool_node_version: "2"
tool_configurations: {}
tool_parameters:
  arg0:
    type: mixed
    value: "{{#sys.user_id#}}"
  arg1:
    type: mixed
    value: "{{#1777528600555.filename#}}"
  arg2:
    type: mixed
    value: "{{#1777528600555.size#}}"
  arg3:
    type: mixed
    value: "{{#1777528600555.extension#}}"
  arg4:
    type: mixed
    value: "{{#1777531848054.text#}}"
  arg5:
    type: mixed
    value: "{{#1777525141446.result#}}"
  arg6:
    type: mixed
    value: "{{#1777527355844.text#}}"
  arg7:
    type: mixed
    value: null
  arg8:
    type: mixed
    value: null
  arg9:
    type: mixed
    value: null
  query:
    type: mixed
    value: |
      INSERT INTO agent_test.ai_document_parse_record (
          user_id,
          file_name,
          file_size,
          file_extension,
          document_summary,
          md_table_content,
          json_table_content
      )
      VALUES (
          $arg0,
          $arg1,
          $arg2,
          $arg3,
          $arg4,
          $arg5,
          $arg6
      );
selected: false
```

When writing a new table, map every dynamic value to an `argN` and keep SQL
static. Do not assemble SQL by string interpolation in an LLM prompt.

## `spance/db_client_node` Read Template

```yaml
title: "读取摘要放到上下文里"
type: tool
is_team_authorization: true
provider_id: spance/db_client_node/db_client_node
provider_name: spance/db_client_node/db_client_node
provider_type: builtin
plugin_id: spance/db_client_node
plugin_unique_identifier: spance/db_client_node:0.1.47@60965f21262129b75b2e01543190ab65021b75b55441532f77f88fcd7b71095d
tool_name: postgres_node_5
tool_label: "PostgreSQL 客户端(5)"
tool_description: "读写PostgreSQL客户端，最多5个参数。"
tool_node_version: "2"
tool_configurations: {}
tool_parameters:
  arg0:
    type: mixed
    value: "{{#sys.user_id#}}"
  arg1:
    type: mixed
    value: null
  arg2:
    type: mixed
    value: null
  arg3:
    type: mixed
    value: null
  arg4:
    type: mixed
    value: null
  query:
    type: mixed
    value: |
      SELECT
          id,
          file_name,
          document_summary
      FROM agent_test.ai_document_parse_record
      WHERE user_id = $arg0
      ORDER BY created_at ASC;
selected: false
```

Use this pattern to load candidate documents/summaries into a later LLM prompt.

## Duplicate Check Pattern

```yaml
tool_parameters:
  arg0:
    type: mixed
    value: "{{#sys.user_id#}}"
  arg1:
    type: mixed
    value: "{{#1777528600555.filename#}}"
  arg2:
    type: mixed
    value: null
  arg3:
    type: mixed
    value: null
  arg4:
    type: mixed
    value: null
  query:
    type: mixed
    value: |
      SELECT EXISTS (
          SELECT 1
          FROM agent_test.ai_document_parse_record
          WHERE user_id = $arg0
            AND file_name = $arg1
      ) AS file_exists;
```

Follow with an `if-else` condition against the tool output. Inspect the imported
tool output shape in Dify (`data`, `text`, or `result`) because plugin versions
can differ.

## `hjlarry/database` SQL Execute Template

Use this after an LLM creates a SELECT and a parameter-extractor returns a clean
`SQL` string.

```yaml
title: "查询具体需要的数据"
type: tool
is_team_authorization: true
provider_id: hjlarry/database/database
provider_name: hjlarry/database/database
provider_type: builtin
plugin_id: hjlarry/database
plugin_unique_identifier: hjlarry/database:0.0.6@534bc26cf5bc4ff6b5557457452287ccc71f00eef9378784c4f43ca49954ca2f
tool_name: sql_execute
tool_label: "SQL Execute"
tool_description: "此工具用于在已存在的数据库中执行 SQL 查询。"
tool_node_version: "2"
tool_configurations:
  config_options:
    type: mixed
    value: null
  format:
    type: constant
    value: json
tool_parameters:
  db_uri:
    type: mixed
    value: null
  query:
    type: mixed
    value: "{{#1777540352910.SQL#}}"
selected: false
```

If the target workspace has no database authorization, set `db_uri` from an
environment variable instead of hardcoding a secret:

```yaml
tool_parameters:
  db_uri:
    type: mixed
    value: "{{#env.DB_URI#}}"
  query:
    type: mixed
    value: "{{#1777540352910.SQL#}}"
```

## NL2SQL Retrieval Pattern

1. `spance/db_client_node` reads summaries and filenames for the current user.
2. LLM receives user question plus summary list and outputs a SQL query or empty
   string.
3. `parameter-extractor` extracts field `SQL`.
4. `if-else` checks `SQL` is `not empty`.
5. `hjlarry/database` executes the SQL in `json` format.
6. `template-transform` optionally formats the JSON result.
7. LLM or `answer` responds to the user.

Prompt guard for step 2:

```text
Generate SQL only. If the document cannot be determined, output an empty string.
Rules:
- SELECT only.
- Query only whitelisted fields: json_table_content.
- Table: agent_test.ai_document_parse_record.
- Always include user_id = '{{#sys.user_id#}}' or a parameter-bound equivalent.
- Match file_name exactly from the provided list. Do not invent file names.
- No markdown fences, no explanation.
```

For stronger safety, do not let the LLM insert `sys.user_id` directly into SQL.
Instead, have it select a file name or ID, then use a fixed parameterized SQL tool
node with `$arg0`/`$arg1`.

## SQL Safety Checklist

- Use `$argN` placeholders for user/file/model values.
- Never leave a trailing comma before `)` in `INSERT` column lists.
- For public templates, avoid `DELETE`, `UPDATE`, `DROP`, `TRUNCATE`, and `ALTER`
  unless the workflow is explicitly an admin workflow.
- Validate LLM-generated SQL with a parameter-extractor and an `if-else` gate.
- Restrict SELECT queries to expected schemas and columns.
- Do not put DB URI passwords in the DSL; use Dify authorization or `env.DB_URI`.
- Tool output field names vary by plugin. After import, inspect the tool node's
  actual output and adjust downstream selectors.
