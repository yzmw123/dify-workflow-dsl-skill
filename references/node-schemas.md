# Node Schemas

All snippets below show the `data:` payload. Wrap them with the standard node
wrapper from `dsl-structure.md`.

## Contents

- Basic flow: start, end, answer
- Reasoning and transform: llm, code, template-transform
- Branching and extraction: if-else, question-classifier, parameter-extractor
- External access: http-request, tool, datasource
- Variables and documents: variable-aggregator, assigner, document-extractor,
  list-operator
- Knowledge: knowledge-retrieval, knowledge-index
- Agents and containers: agent, iteration, loop
- Human/trigger/canvas nodes: human-input, trigger-schedule, trigger-webhook,
  trigger-plugin, custom-note

## start

```yaml
title: "开始"
type: start
variables:
  - label: "输入文本"
    variable: input_text
    type: paragraph       # text-input | paragraph | select | number | url | file | file-list | json | checkbox
    required: true
    max_length: 50000
```

For `advanced-chat`, start variables are often empty and user input comes from
`{{#sys.query#}}` and `{{#sys.files#}}`.

## end

```yaml
title: "结束"
type: end
outputs:
  - variable: result
    value_selector: ["1770000000001", text]
```

Use `end` for `workflow` apps.

## answer

```yaml
title: "直接回复"
type: answer
answer: "{{#1770000000001.text#}}"
variables: []
```

Use `answer` for `advanced-chat` apps. Multiple branches may each end in their own
answer node.

## llm

```yaml
title: "LLM"
type: llm
model:
  provider: langgenius/tongyi/tongyi
  name: qwen3.5-flash
  mode: chat
  completion_params:
    temperature: 0.3
prompt_template:
  - id: 9e05cb8e-0000-4000-9000-000000000001
    role: system
    text: "You are a precise assistant."
  - id: 9e05cb8e-0000-4000-9000-000000000002
    role: user
    text: "{{#sys.query#}}"
context:
  enabled: false
  variable_selector: []
memory:
  query_prompt_template: "{{#sys.query#}}\n\n{{#sys.files#}}"
  role_prefix:
    assistant: ""
    user: ""
  window:
    enabled: false
    size: 50
vision:
  enabled: false
selected: false
```

`context.enabled: true` is used when feeding knowledge retrieval results into the
LLM.

## code

```yaml
title: "清洗 JSON"
type: code
code_language: python3
code: |
  import json

  def main(text: str) -> dict:
      return {"result": json.loads(text)}
variables:
  - value_selector: ["1770000000001", text]
    variable: text
outputs:
  result:
    type: object
selected: false
```

The function must be named `main`; it must return a dict with keys matching
`outputs`.

## if-else

```yaml
title: "条件分支"
type: if-else
cases:
  - id: "true"
    case_id: "true"
    logical_operator: and
    conditions:
      - id: 0b5f09ef-0000-4000-9000-000000000001
        variable_selector: ["1770000000000", input_text]
        comparison_operator: contains
        value: "合同"
        varType: string
selected: false
```

Branch edge `sourceHandle` must equal the target case ID.

Common comparison operators: `contains`, `not contains`, `is`, `is not`, `empty`,
`not empty`, `start with`, `end with`, `=`, `≠`, `>`, `<`, `≥`, `≤`.

## question-classifier

```yaml
title: "问题分类器"
type: question-classifier
model:
  provider: langgenius/tongyi/tongyi
  name: qwen3.5-flash
  mode: chat
  completion_params:
    temperature: 0
query_variable_selector: ["sys", query]
classes:
  - id: "1"
    name: "上传文件"
  - id: "2"
    name: "查询历史"
instruction: "将用户问题分类到最合适的一类。"
vision:
  enabled: false
selected: false
```

Classifier branch edge handles are class IDs.

## parameter-extractor

```yaml
title: "参数提取器"
type: parameter-extractor
instruction: "从输入中提取 SQL；没有 SQL 时返回空字符串。"
model:
  provider: langgenius/tongyi/tongyi
  name: qwen3.5-plus
  mode: chat
  completion_params:
    temperature: 0.1
parameters:
  - name: SQL
    description: "SQL query"
    required: false
    type: string
query: ["1770000000001", text]
reasoning_mode: prompt
vision:
  enabled: false
selected: false
```

Use after an LLM when you need a strict structured field before an `if-else` or
tool call.

## http-request

```yaml
title: "HTTP 请求"
type: http-request
method: post
url: "https://api.example.com/parse"
headers: "Content-Type: application/json"
params: ""
body:
  type: json
  data:
    - id: body-1
      key: text
      type: string
      value: "{{#1770000000000.input_text#}}"
authorization:
  type: no-auth
timeout:
  connect: 10
  read: 60
  write: 10
retry_config:
  retry_enabled: false
selected: false
```

Outputs commonly referenced: `body`, `status_code`, `headers`, `files`.

## template-transform

```yaml
title: "模板"
type: template-transform
variables:
  - variable: rows
    value_selector: ["1770000000001", data]
template: |
  {% for row in rows %}
  - {{ row.file_name }}: {{ row.document_summary }}
  {% endfor %}
selected: false
```

Output is `output`.

## variable-aggregator

```yaml
title: "汇总"
type: variable-aggregator
output_type: string
variables:
  - ["1770000000001", text]
  - ["1770000000002", text]
selected: false
```

Use to merge mutually exclusive branch outputs before `end`.

## assigner / variable-assigner

```yaml
title: "写入会话变量"
type: assigner
items:
  - variable_selector: [conversation, Memory]
    input_type: variable
    value_selector: ["1770000000001", output]
    operation: over-write
selected: false
```

Some newer exports use `variable-assigner`; follow the target workspace export
style if editing an existing file.

## document-extractor

```yaml
title: "文档提取器"
type: document-extractor
variable_selector: ["sys", files]
selected: false
```

Output is usually `text`. For file lists, pair with code/list nodes if you need
the first file metadata.

## list-operator

```yaml
title: "取第一个文件"
type: list-operator
filter_by:
  enabled: false
order_by:
  enabled: false
extract_by:
  enabled: true
  serial: first
var_type: array[file]
variable: ["sys", files]
selected: false
```

Use for file list or array extraction before a code/tool node.

## knowledge-retrieval

```yaml
title: "知识检索"
type: knowledge-retrieval
dataset_ids:
  - "dataset-id"
query_variable_selector: ["sys", query]
retrieval_mode: multiple
multiple_retrieval_config:
  top_k: 4
  reranking_enable: false
  score_threshold_enabled: false
  score_threshold: 0
metadata_filtering_mode: disabled
selected: false
```

Feed results to an LLM through `context.variable_selector`.

## tool

```yaml
title: "工具"
type: tool
provider_id: langgenius/firecrawl/firecrawl
provider_name: langgenius/firecrawl/firecrawl
provider_type: builtin   # builtin | api | workflow | mcp
plugin_id: langgenius/firecrawl
plugin_unique_identifier: langgenius/firecrawl:0.0.5@...
tool_name: scrape
tool_label: "单页面抓取"
tool_description: "Scrape a page"
tool_node_version: "2"
tool_configurations:
  formats:
    type: constant
    value: markdown
tool_parameters:
  url:
    type: mixed
    value: "https://example.com?q={{#sys.query#}}"
selected: false
```

Tool output fields depend on the plugin. Common fields are `text`, `data`,
`result`, `json`, `files`, and `output`.

`plugin_id`, `plugin_unique_identifier`, and `tool_node_version` are common in
newer marketplace/package exports but are not universal. Built-in, MCP, API, and
workflow tools may omit them. Preserve these fields when copying from an export;
do not invent exact plugin identifiers.

## agent

```yaml
title: "Agent"
type: agent
agent_strategy_provider_name: langgenius/agent/agent
agent_strategy_name: function_calling
agent_strategy_label: FunctionCalling
agent_parameters:
  model:
    type: constant
    value:
      provider: langgenius/tongyi/tongyi
      name: qwen3.5-flash
      mode: chat
      completion_params:
        temperature: 0.3
  query:
    type: constant
    value: "{{#sys.query#}}"
  instruction:
    type: constant
    value: "Answer with tool support when useful."
  tools:
    type: constant
    value: []
output_schema: null
selected: false
```

## iteration

```yaml
title: "迭代"
type: iteration
iterator_selector: ["1770000000001", items]
output_selector: ["1770000000003", output]
output_type: array[string]
is_parallel: false
parallel_nums: 10
start_node_id: "1770000000002"
selected: false
```

Exported Dify graphs also include an `iteration-start` helper node with wrapper
`type: custom-iteration-start` and internal child nodes marked `isInIteration`.

## loop

```yaml
title: "循环"
type: loop
loop_count: 5
break_conditions:
  - id: 6db087e6-0000-4000-9000-000000000001
    variable_selector: ["1770000000003", done]
    comparison_operator: is
    value: "true"
    varType: boolean
start_node_id: "1770000000002"
selected: false
```

Exported loop internals use `loop-start` and mark child edges/nodes with
`isInLoop`. Dify's current node enum also includes `loop-end`; copy loop internals
from an export when the loop contains nested branches or multiple exits.

## datasource

```yaml
title: "数据源"
type: datasource
provider_id: langgenius/notion/notion
provider_name: langgenius/notion/notion
provider_type: builtin
datasource_name: pages
datasource_label: "Pages"
datasource_parameters: {}
selected: false
```

Datasource nodes are plugin-backed; copy from a real export whenever possible.

## knowledge-index

```yaml
title: "知识库写入"
type: knowledge-index
dataset_id: "dataset-id"
index_chunk_variable_selector: ["1770000000001", text]
keyword_number: 10
retrieval_model:
  top_k: 3
  score_threshold_enabled: false
  score_threshold: 0.5
selected: false
```

Use only when the target Dify version supports knowledge indexing in workflows.

## human-input / human-feedback

```yaml
title: "人工确认"
type: human-input
variables:
  - label: "是否继续"
    variable: approved
    type: select
    required: true
    options:
      - label: "继续"
        value: "yes"
      - label: "停止"
        value: "no"
selected: false
```

These nodes are version-sensitive. Prefer copying an export from the target Dify
workspace for production DSL.

## trigger-schedule

```yaml
title: "定时触发"
type: trigger-schedule
mode: visual
frequency: daily
timezone: Asia/Shanghai
visual_config:
  time: "09:00 AM"
cron_expression: ""
selected: false
```

Schedule triggers support `mode: visual` or `mode: cron`; visual frequency can be
`hourly`, `daily`, `weekly`, or `monthly`. Official export resets schedule config,
so copy from a current workspace export for production use.

## trigger-webhook

```yaml
title: "Webhook 触发"
type: trigger-webhook
webhook_url: ""
webhook_debug_url: ""
method: POST
content_type: application/json
headers: []
params: []
body: []
async_mode: true
status_code: 200
response_body: ""
variables: []
selected: false
```

Official export clears webhook URLs. Keep them empty in public DSL and let the
target workspace generate or configure them after import.

## trigger-plugin

```yaml
title: "插件事件触发"
type: trigger-plugin
provider_id: author/plugin/provider
provider_name: author/plugin/provider
provider_type: builtin
plugin_id: author/plugin
plugin_unique_identifier: author/plugin:0.0.1@...
event_name: event_name
event_label: "Event label"
event_parameters: {}
event_configurations: {}
output_schema: {}
config: {}
selected: false
```

Official export clears `subscription_id`. Plugin triggers are highly
plugin-specific; use a fresh minimal export from the target Dify workspace before
claiming production reliability.

## custom-note

```yaml
title: ""
type: ""
text: "Canvas note"
theme: blue
author: ""
showAuthor: false
width: 260
height: 120
selected: false
```

The node wrapper is `type: custom-note`. Notes are valid non-executable canvas
annotations and may have an empty `data.type`.
