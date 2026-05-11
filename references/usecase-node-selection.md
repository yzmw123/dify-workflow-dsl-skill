# Use Case And Node Selection

Use this reference when turning a user's business requirement into a Dify
Workflow or Chatflow graph. Default to `workflow` unless the requirement clearly
needs a conversational Chatflow.

## Mode Selection

| User need | Prefer | Why |
| --- | --- | --- |
| Run once, process an input, return structured results | `workflow` | Clear start variables and `end` outputs |
| Batch file/table/document processing | `workflow` | Iteration, document extraction, code, and multiple end branches are easier to control |
| Cron, webhook, plugin event, or integration automation | `workflow` | Trigger nodes are workflow-native; the terminal action may be a tool side effect |
| Reusable subflow called by another Dify workflow | `workflow` | Exported examples commonly expose workflows as tool providers |
| User chats over multiple turns | `advanced-chat` | Needs memory and `answer` nodes |
| Chat input, uploaded chat files, and immediate answer | `advanced-chat` | Uses `sys.query`, `sys.files`, and optional conversation variables |
| FAQ/support bot with retrieval and multi-turn follow-up | `advanced-chat` | Retrieval + LLM + answer with memory |

If the user does not specify a mode, say: "I will build this as `workflow` by
default; if you need Chatflow behavior, I will switch it to `advanced-chat`."
Then proceed unless mode ambiguity would change import-critical inputs or
terminal nodes.

## Trigger Selection

| Trigger need | Node pattern | Notes |
| --- | --- | --- |
| User manually runs app with form fields | `start -> ... -> end` | Define start variables with `required`, `type`, and labels |
| Chat message starts flow | `start -> ... -> answer` in `advanced-chat` | Usually use `{{#sys.query#}}` rather than start variables |
| Scheduled digest or sync | `trigger-schedule -> agent/code/tool` | Public examples may end at Slack/Feishu/email tool when the job is side-effect only |
| External system event | `trigger-webhook -> code -> if-else -> tool` | Parse payload in code; keep exported webhook URLs empty |
| Plugin event | `trigger-plugin -> classifier/agent/tool` | Preserve exported plugin trigger fields; do not invent event schema |
| Another workflow calls this flow | Tool node with `provider_type: workflow` | Provider IDs are workspace-specific; copy from export |

## Common Business Patterns

| Requirement | Good graph shape | Nodes to consider |
| --- | --- | --- |
| Summarize or rewrite text | `start -> llm -> end` | `llm`, `template-transform` |
| Generate an email or report draft | `start -> llm -> template-transform -> end` | LLM for content, template for fixed output shape |
| Classify intent then route | `start -> question-classifier/if-else -> branch -> answer/end` | `question-classifier` for semantic classes, `if-else` for deterministic fields |
| Extract strict fields from unstructured text | `start -> llm -> parameter-extractor/code -> end` | Use `parameter-extractor` when model-backed extraction is enough; use `code` for JSON cleanup |
| Validate forms or business rules | `document-extractor/code -> if-else -> end/email` | Code is best for deterministic validation; use branches for deficiency messages |
| Process uploaded PDFs/Excel/ZIPs | `start(file) -> document-extractor/list-operator/tool -> code -> end` | Use file converter or extractor tools when native extractor is insufficient |
| Iterate over rows, files, or chunks | `start -> code/list-operator -> iteration -> template-transform -> end` | Copy exported iteration internals when nested branches are involved |
| Search/research with current data | `start/trigger -> agent -> tool -> end/tool` | Agent works when tool choice is dynamic; always model recency checks explicitly |
| RAG answer over a knowledge base | `start -> knowledge-retrieval -> llm -> answer/end` | Enable LLM `context` and set retrieval top-k/thresholds |
| Update KB metadata or external records | `start/trigger -> http-request/tool -> code -> if-else -> end` | Keep dataset/document IDs and tokens as variables or placeholders |
| Send Slack/Feishu/email notifications | `trigger/code/llm -> tool` | Output may be side-effect only; preserve tool `paramSchemas` and auth fields |
| Sync Dify DSLs to GitHub | `trigger-schedule/start -> code -> iteration/code -> end` | One code node can be safer than many graph nodes for stateful API/file logic |
| Audit or vulnerability-check DSL | `start(file/text) -> code/http -> llm -> end` | Parse YAML first, then ask LLM to reason over normalized facts |
| Build flowcharts from DSL | `start -> code/http -> llm/template -> end` | Prefer structured parse before diagram generation |

## Node Choice Heuristics

- Use `code` for deterministic parsing, normalization, validation, deduplication,
  batching, and API response shaping.
- Use `llm` for natural-language reasoning, summarization, rewriting, extraction
  that tolerates model judgment, and final prose.
- Use `parameter-extractor` when downstream branches/tools need a few typed fields
  from model output.
- Use `question-classifier` when semantic intent classes drive routing.
- Use `if-else` when conditions are explicit: empty/non-empty, equals, contains,
  numeric comparison, validation result, or file count.
- Use `template-transform` for stable Markdown, JSON-like text, email bodies, or
  report assembly after data is already available.
- Use `variable-aggregator` to merge mutually exclusive branch outputs before a
  shared `end` or `answer`.
- Use `assigner` only for conversation/environment variable writes, mostly in
  Chatflow memory/state scenarios.
- Use `agent` when tool choice or multi-step research is dynamic. For fixed tool
  calls, normal tool nodes are more predictable.
- Use `http-request` for plain REST APIs when no Dify plugin exists; use tool
  nodes when a plugin provides auth, schemas, and stable outputs.

## File And Document Workflows

- For single file inputs in `workflow`, define a start variable with `type: file`.
- For multiple files, use `type: file-list`, then `list-operator` or `iteration`.
- Keep global `features.file_upload.enabled: false` for workflow-mode start file
  variables unless copying an export that says otherwise.
- Document-heavy workflows often need a guard branch for missing files, conversion
  failure, empty extracted text, and oversized content.
- For Excel extraction, public examples often combine file conversion tools,
  `document-extractor`, code cleanup, and an LLM only after tabular text is stable.

## Integration Workflows

- For Slack, Feishu, email, and other notification tools, preserve exported
  `paramSchemas`, `params`, `tool_configurations`, `is_team_authorization`,
  `plugin_unique_identifier`, and dependency entries.
- For webhook workflows, parse the raw payload with `code` before branching.
- For scheduled workflows, include timezone and cron/visual config, but expect the
  target workspace to reconfigure schedules after import.
- For workflow-provider tools, provider IDs are usually workspace UUIDs. Treat them
  as non-portable unless the user provides an export from the target workspace.

## Reliability Rules

- Use an exported node as the source of truth for any rare plugin, trigger, agent
  strategy, or workflow-provider tool.
- Prefer a small number of robust code nodes over sprawling graphs when the logic
  is mainly state management, API pagination, diffing, or file packaging.
- Add explicit failure outputs for business workflows: invalid input, no data,
  upstream API failed, unauthorized, or partial success.
- For user-facing generated files or messages, separate reasoning/extraction from
  formatting: LLM or code first, then `template-transform` or tool.
