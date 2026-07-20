# Real-World YAML Study

This reference records observations from real public Dify DSL files. Use it to
calibrate generated YAML against workflows that people actually exported and ran.
For new DSL generation, do not treat these public files as the latest schema
authority. The corpus predates Dify 1.16's DSL `0.7.0`; use official source for
the target version and this corpus for graph/design evidence.

## Contents

- Corpus checked
- Additional corpus checked on 2026-05-11
- Detailed samples
- Additional detailed samples
- Observed version and mode reality
- Tool node reality
- Trigger and integration reality
- Business workflow reality
- Dependency reality
- Canvas and helper nodes
- Generator project lessons
- Rule corrections for this skill

## Corpus Checked

Repositories inspected:

- `BannyLon/DifyAIA`: 38 YAML files, all 38 parsed as Dify apps.
- `svcvit/Awesome-Dify-Workflow`: 46 YAML files, 45 parsed as Dify apps.
- `wwwzhouhui/dify-for-dsl`: 92 YAML files, 89 parsed as Dify apps.

Detailed sample: 39 representative DSL files, selected by recent commit date and
workflow diversity, with extra emphasis on `Awesome-Dify-Workflow`.

Version scan on 2026-05-07:

- `BannyLon/DifyAIA`: `0.1.2`-`0.3.1`, no `0.6.0`.
- `svcvit/Awesome-Dify-Workflow`: `0.1.0`-`0.3.0`, no `0.6.0`.
- `wwwzhouhui/dify-for-dsl`: `0.1.2`-`0.5.0`, no `0.6.0`.

Conclusion: these samples are valuable real-world DSL evidence, but only as
legacy/import-shape and workflow-design material. Target Dify 1.16.x generation
from `references/official-0.7-target.md`; retain the 0.6.0 reference for 1.15.x.

## Additional Corpus Checked On 2026-05-11

Repositories inspected:

- `g-krishna0/dify-export-test`: 87 YAML files under `dsl/`, all 87 parsed as
  Dify apps. All use `version: 0.3.1`; modes are 50 `workflow` and 37
  `advanced-chat`.
- `Petrus-Han/dify-usecase-playground`: 3 YAML files under `usecases/`, all 3
  parsed as Dify apps. Two use `version: 0.5.0`; one uses `version: 0.6.0`; all
  are `workflow`.
- `TheOneWithChair/Dify-DSL-generator`: not a sample DSL corpus, but useful as a
  competing generation design. It uses a UI intake for workflow type, complexity,
  required tools, expected input/output, validation, refinement, and a node-doc
  library. It depends on Gemini, which this skill does not need; here the reusable
  lesson is better intake and reference organization.

Aggregate public corpus after this pass: 262 parsed Dify app DSL files
(172 earlier files + 90 new files). Most are still legacy exports. The new
`dify-usecase-playground` sample proves public `0.6.0` exports exist, but the
sample size is tiny; official Dify source remains the authority for new DSL.

New corpus stats:

- `dify-export-test`: node counts range from 3 to 190, median 15. Top node types:
  `code` 744, `answer` 561, `if-else` 507, `assigner` 416,
  `template-transform` 259, `llm` 202, `http-request` 133, `tool` 90, `end` 100.
- `dify-export-test` tool providers: `workflow` 69 and `builtin` 21. This is
  strong evidence that exported Dify workflows are often composed as reusable
  sub-workflow tools.
- `dify-usecase-playground`: node counts 3, 8, and 14. Node types include
  `trigger-schedule`, `trigger-webhook`, `trigger-plugin`, `agent`, `tool`, `llm`,
  `question-classifier`, `if-else`, and `code`.
- New dependency evidence remains mostly marketplace: `dify-export-test` has 72
  marketplace dependency entries; `dify-usecase-playground` has 4.

## Detailed Samples

### BannyLon/DifyAIA

- `文粹 AI——批量文档总结神器.yml`: advanced-chat, `0.3.1`, document extractor + iteration.
- `票录精灵.yml`: advanced-chat, `0.3.1`, Feishu Base add records tool.
- `架构魔法师.yml`: advanced-chat, `0.3.1`, document extractor + Mermaid converter tool.
- `智票通 - 批量发票智能解析 (1).yml`: advanced-chat, `0.3.1`, invoice parsing, branches, Feishu spreadsheet tools.
- `PDF 翻译 Agent.yml`: agent-chat, `0.3.1`, `model_config.agent_mode` with MCP tools and no workflow graph.
- `Zapier MCP test.yml`: advanced-chat, `0.3.0`, MCP tool node.
- `实时热点新闻聚合引擎（每日简报版）.yml`: advanced-chat, `0.3.0`, many RSS tools, code nodes, SMTP tool, aggregator.
- `文生视频.yml`: advanced-chat, `0.3.0`, text-to-video tool.
- `文思泉涌.yml`: workflow, `0.3.0`, iteration and code.
- `智能合同卫士.yml`: workflow, `0.2.0`, document extraction and Markdown export tools.
- `知识图解（KnowGraph）.yml`: workflow, `0.1.5`, nested iterations, notes, Jina tool, multiple ends.

### svcvit/Awesome-Dify-Workflow

- `小支付-DEMO.yml`: advanced-chat, `0.3.0`, payment tools, assigner, branches.
- `Artifact.yml`: advanced-chat, `0.2.0`, minimal LLM answer.
- `MCP-amap.yml`: advanced-chat, `0.1.5`, agent node with MCP server parameter.
- `图文知识库.yml`: advanced-chat, `0.1.5`, knowledge retrieval + LLM.
- `Demo-tod_agent.yml`: advanced-chat, `0.1.5`, agent + conditional answer.
- `记忆测试.yml`: advanced-chat, `0.1.2`, many assigners and conversation memory patterns.
- `根据用户的意图进行回复.yml`: workflow, `0.1.0`, question classifier + knowledge retrieval + aggregator.
- `文章仿写-单图_多图自动搭配.yml`: workflow, `0.1.0`, workflow provider tools, parameter extractors, iteration.
- `搜索大师.yml`: advanced-chat, `0.1.0`, HTTP, search tools, iterations.
- `simple-kimi.yml`: advanced-chat, `0.1.2`, list-operator, document extractor, multiple tool branches.
- `json_translate.yml`: workflow, `0.1.3`, code + iteration + translate tool.
- `runLLMCode.yml`: workflow, `0.1.4`, HTTP request + code execution pattern.
- `Text to Card Iteration.yml`: workflow, `0.1.0`, parameter extractor + template.
- `全书翻译.yml`: workflow, `0.1.2`, iteration plus canvas notes.
- `旅行Demo.yml`: advanced-chat, `0.1.5`, agent + assigners + templates.

### wwwzhouhui/dify-for-dsl

- `51-dify案例分享-...财报分析...HTML 可视化.yml`: advanced-chat, `0.5.0`, MinerU parse file + LLM + code.
- `88-dify案例分享-...Nano Banana2AI画图.yml`: advanced-chat, `0.4.0`, package dependency and private image tool.
- `85-dify案例分享-...Sora2...yml`: advanced-chat, `0.4.0`, package dependency and video tool.
- `86-dify案例分享-Qwen3-VL+Dify...yml`: advanced-chat, `0.4.0`, HTTP + code + if-else multimodal flow.
- `84-dify案例分享-...文生图+图生图插件...yml`: advanced-chat, `0.4.0`, two image tools and branch.
- `83-dify案例分享-...即梦 4.0 多图生成...yml`: advanced-chat, `0.4.0`, HTTP/code multi-answer flow.
- `79-dify案例分享-...MCP工具...yml`: advanced-chat, `0.3.0`, LLM + code + agent.
- `76-dify案例分享-...通用票据识别...yml`: advanced-chat, `0.3.0`, multiple HTTP/code/LLM branches.
- `74-dify案例分享-...秘塔搜索...yml`: workflow, `0.3.0`, 26-node search workflow, many code/end branches.
- `73-dify案例分享-...发票申请预览...yml`: advanced-chat, `0.3.0`, Excel tool + LLM + code.
- `69-dify案例分享-数学公式识别工作流.yml`: advanced-chat, `0.3.0`, PDF process tool + aggregator.
- `58-dify案例分享-中小学数学错题本-生成同类型题.yml`: advanced-chat, `0.3.0`, database, time, Markdown export, iteration, question classifier.
- `57-dify案例分享-中小学数学错题本-错题收集篇.yml`: advanced-chat, `0.3.0`, database + PDF process + iteration.

## Additional Detailed Samples

### g-krishna0/dify-export-test

- `Dify_Dsl_Github_Sync_Cron_OPTIMISED__v30.yml`: workflow, `0.3.1`, scheduled
  or manually run DSL sync pattern. Uses code-heavy state/diff/export logic with
  iteration helpers. Lesson: when logic is API pagination, state files, GitHub
  commits, and normalized diffs, a few robust code nodes are clearer than a large
  graph of small nodes.
- `Auto_KB_Metadata_Extractor_v4.1.yml`: workflow, `0.3.1`, Dify Knowledge Base
  metadata update. Uses HTTP requests, code parsing, if-else validation, LLM
  extraction, iteration, and multiple error end paths. Lesson: external Dify API
  automations need explicit failure branches for missing IDs, empty segments, API
  errors, and partial success.
- `Graph_Data_Extractor.yml`: workflow, `0.3.1`, file upload graph/chart data
  extraction. Uses several LLM passes plus code/template. Lesson: visual or
  document extraction workflows benefit from separating detection, extraction,
  anti-hallucination verification, and final table formatting.
- `Table_Data_Extractor__PDF_v6.yml`: workflow, `0.3.1`, PDF table extraction.
  Uses code-heavy pdfplumber-style extraction, LLM cleanup, iteration, and
  template output. Lesson: for large documents, deterministic extraction before
  LLM cleanup saves tokens and reduces hallucination.
- `Travel_Expenses_Form3_Validator.yml`: workflow, `0.3.1`, form validation and
  deficiency email generation. Uses document extraction, knowledge retrieval,
  variable aggregation, template transform, code, and end. Lesson: validation
  workflows should use code for rule checks and templates for stable messages.
- `SharePoint_Connector_Graph_API.yml`: workflow, `0.3.1`, Microsoft Graph
  connector without a Dify plugin. Uses HTTP request, code, if-else, and variable
  aggregator. Lesson: when no plugin exists, REST + code can emulate a connector,
  but secrets must be environment variables/placeholders.
- `D11QAEmail.yml`: advanced-chat, `0.3.1`, PC inspection support bot that calls
  reusable workflows for bilingual processing, file validation, Excel extraction,
  FAQ lookup, and email generation. Lesson: Chatflow is appropriate when the user
  stays in a support conversation and reusable workflow tools do the heavy work.
- `The_Smart_Voyager.yml`: advanced-chat, `0.3.1`, travel planner that delegates
  experience, visa, logistics, and itinerary steps to workflow-provider tools.
  Lesson: complex assistants can be Chatflow shells over smaller Workflow tools.
- Repeated Excel extractor files: workflow, `0.3.1`, file upload plus
  `document-extractor`, `list-operator`, `excel_2_csv` tool, code cleanup, LLM,
  and several end branches. Lesson: file conversion and deterministic cleanup
  should happen before asking an LLM to infer fields.

Common tool names in this repo:

- Workflow-provider tools: `comBilingualWorkflow` 19, `excel_extractor_v4` 17,
  `comFileValidator` 16, `email_gen_v1` 6, `PC_inspection` 4.
- Built-in tools: `md_to_pdf` 11, `excel_2_csv` 7, `word_2_pdf` 2, `zip` 1.

### Petrus-Han/dify-usecase-playground

- `daily-news-slack/workflow.yml`: workflow, `0.5.0`, schedule trigger -> agent
  with Yahoo/current-time tools -> Slack webhook. Lesson: scheduled digests are
  Workflow, not Chatflow; the output can be a side-effect tool call.
- `slack-news-researcher/workflow.yml`: workflow, `0.5.0`, plugin trigger ->
  question classifier -> agent/LLM branches -> Slack webhook. Lesson: message
  event workflows can classify whether to use research tools or generate a normal
  response before sending back to Slack.
- `confluence-to-feishu/workflow.yml`: workflow, `0.6.0`, webhook trigger ->
  code payload parsing -> if-else event routing -> Feishu message tools. Lesson:
  webhook automations should normalize payloads in code first, then branch by
  event type and build deterministic message cards.

## Observed Version And Mode Reality

- Public DSLs commonly use `0.1.0` to `0.5.0`; not every runnable workflow uses
  the latest official DSL version.
- The first three inspected repositories had no parsed `0.6.0` exports. A later
  2026-05-11 scan found one public `0.6.0` workflow in
  `Petrus-Han/dify-usecase-playground`, so public `0.6.0` evidence exists but is
  still sparse.
- `advanced-chat` dominates recent examples; `workflow` remains common for batch
  runs and multi-end automation.
- Triggered integration automations in the new samples use `workflow`, even when
  they respond into Slack/Feishu rather than returning a normal `end` output.
- `agent-chat` examples often use top-level `model_config`, not
  `workflow.graph.nodes`.
- Some YAML files write `version: 0.3.0` without quotes. YAML parsers commonly
  keep multi-dot versions as strings, but generated DSL should still quote
  versions for safety.

## Tool Node Reality

Real tool nodes vary more than the clean schema:

- `provider_type` appears as `builtin`, `api`, `workflow`, and `mcp`.
- Many valid tool nodes do not include `plugin_id` or `plugin_unique_identifier`
  inside the node, even when the app has top-level dependencies.
- `tool_node_version` is useful but not always present.
- `paramSchemas`, `params`, and `is_team_authorization` appear frequently in
  newer exports and should be preserved when copied from real DSL.
- MCP tools can appear as normal workflow tool nodes or inside
  `model_config.agent_mode.tools`.
- Workflow-provider tools can reference local/custom workflows with UUID-like
  provider IDs and no marketplace dependency.
- In `dify-export-test`, workflow-provider tools are the majority of tool nodes.
  Treat them as powerful but workspace-specific; never invent provider UUIDs.

## Trigger And Integration Reality

- Real trigger workflows may start with `trigger-schedule`, `trigger-webhook`, or
  `trigger-plugin` instead of a `start` node.
- Public trigger samples may omit an `end` node when the job's purpose is a
  side-effect such as Slack/Feishu notification. For user-run workflows where the
  caller needs returned values, still include `end`.
- Schedule exports include both `cron_expression` and visual config/timezone
  fields; these may need reconfiguration after import.
- Webhook exports keep `webhook_url` and `webhook_debug_url` empty. Do not fill
  them with fake URLs.
- Plugin trigger schemas are plugin-specific. Copy from a current export rather
  than extrapolating.

## Business Workflow Reality

- File and office-document workflows often combine file upload, document
  extraction/conversion tools, code cleanup, LLM interpretation, if-else error
  branches, and templated outputs.
- Enterprise approval, inspection, travel expense, and QA workflows are usually
  `workflow` when they transform or validate records, but `advanced-chat` when a
  human continues asking follow-up questions.
- Integration workflows often need secrets and endpoint IDs as environment
  variables. Public examples sometimes embed placeholders or static-looking
  descriptions; generated DSL should not hardcode real tokens.
- Complex assistant products can be designed as a Chatflow shell that delegates
  deterministic sub-tasks to smaller Workflow apps exposed as workflow-provider
  tools.
- For stateful sync jobs, code nodes can legitimately carry most of the logic
  because Dify graph nodes are less ergonomic for API pagination, diffing,
  packaging, and commit state.

## Generator Project Lessons

`TheOneWithChair/Dify-DSL-generator` is similar in goal but wraps generation in a
Streamlit app and Gemini API. Useful ideas to borrow:

- Ask or infer workflow type early: Chatflow maps to Dify `advanced-chat`; normal
  automations map to `workflow`.
- Capture expected input, expected output, required tools, and complexity before
  writing YAML.
- Keep node docs in separate files and load only relevant node references.
- Validate and post-process generated YAML instead of trusting raw model output.
- Support refinement of an existing DSL from natural-language feedback.

Differences for this skill:

- Do not require `GEMINI_API_KEY`, `DIFY_API_KEY`, or a Streamlit UI. The agent
  using this skill is the generator.
- Target official `version: "0.7.0"` for new Dify 1.16.x DSL, while treating old
  samples as compatibility/workflow-design evidence.
- Prefer exported plugin/tool nodes for reliability instead of synthesizing exact
  plugin schemas from names alone.

## Dependency Reality

Dependencies are not only marketplace entries.

Marketplace dependency:

```yaml
- current_identifier: null
  type: marketplace
  value:
    marketplace_plugin_unique_identifier: langgenius/openai:0.0.23@...
    version: null
```

Package dependency:

```yaml
- current_identifier: null
  type: package
  value:
    plugin_unique_identifier: wwwzhouhui/nano_banana2_text2image:0.0.1@...
    version: null
```

Official current Dify also supports GitHub-installed plugin dependencies:

```yaml
- current_identifier: null
  type: github
  value:
    repo: author/plugin-repo
    version: 0.0.1
    package: plugin-package-name
    github_plugin_unique_identifier: author/plugin:0.0.1@...
```

Older or custom workflows may have `dependencies: []` even while using built-in,
MCP, API, or workflow tools.

## Canvas And Helper Nodes

- `custom-note` nodes are common in complex public DSLs. They may have empty
  `data.type` and should be treated as canvas annotations, not executable nodes.
- Iteration exports include `iteration` plus `iteration-start` with wrapper
  `custom-iteration-start`.
- Some older iteration child edges lack all newer loop/iteration flags; copying
  a real export is safer than hand-inventing nested graph metadata.

## Rule Corrections For This Skill

- Do not require `plugin_id` or `tool_node_version` for every tool node.
- Do require `provider_id`, `provider_name`, `provider_type`, `tool_name`,
  `tool_label`, and `tool_parameters` for executable workflow tool nodes.
- Preserve `paramSchemas` and `params` when copying a real node.
- Support dependency `type: package` and `type: github` as well as
  `type: marketplace`.
- Treat `custom-note` as valid non-executable metadata.
- Treat `agent-chat`, `chat`, and `completion` as model-config apps, not graph
  workflows, unless a graph is present.
- Default generated apps to `workflow`; switch to `advanced-chat` for Chatflow,
  memory, `sys.query`, `sys.files`, and `answer` nodes.
- Treat trigger-driven Slack/Feishu/webhook/schedule automations as `workflow`.
- Prefer generated `workflow` or `advanced-chat` for new work, but understand
  legacy/public DSLs when reviewing or adapting.
- For new Dify 1.16.x DSL, use official `version: "0.7.0"`; use `"0.6.0"` only
  for Dify 1.15.x compatibility, and borrow graph patterns—not version authority—
  from these older public samples.
