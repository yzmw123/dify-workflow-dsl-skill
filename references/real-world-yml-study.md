# Real-World YAML Study

This reference records observations from real public Dify DSL files. Use it to
calibrate generated YAML against workflows that people actually exported and ran.
For new DSL generation, do not treat these public files as the latest schema
authority; Dify's official current app DSL version is `0.6.0`, while this public
corpus is older.

## Contents

- Corpus checked
- Detailed samples
- Observed version and mode reality
- Tool node reality
- Dependency reality
- Canvas and helper nodes
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
legacy/import-shape and workflow-design material. Target new generation from
`references/official-0.6-target.md`.

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

## Observed Version And Mode Reality

- Public DSLs commonly use `0.1.0` to `0.5.0`; not every runnable workflow uses
  the latest official DSL version.
- None of the three inspected public repositories currently contains a parsed
  `version: "0.6.0"` Dify app DSL file.
- `advanced-chat` dominates recent examples; `workflow` remains common for batch
  runs and multi-end automation.
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
- Prefer generated `workflow` or `advanced-chat` for new work, but understand
  legacy/public DSLs when reviewing or adapting.
- For new generated DSL, use official `version: "0.6.0"` and only borrow graph
  patterns from these older public samples.
