# Dify Workflow DSL Skill

**Dify Workflow DSL Skill** helps an AI coding agent create, modify, review, and
debug Dify Workflow/Chatflow YAML files that can be imported directly into Dify.

I started this project after realizing that building Dify workflows by hand is
powerful but often painfully slow: drag nodes, connect branches, configure tools,
test imports, repeat. Then I noticed Dify supports YAML import/export for
workflows. That led to a simple idea: why not let AI learn how Dify writes
workflows, and then ask AI to write the DSL for us?

This skill is the result of that idea. It targets Dify's official current app
DSL version, `0.6.0`, by studying Dify's open-source code, exported Dify DSL
files, and public Dify workflow DSL examples from GitHub, then turning those
patterns into a reusable skill.

During the research process, I systematically studied Dify's official source
code, my own exported DSL files, and multiple public DSL example repositories.
Those public repositories include 262 parseable Dify app DSL files, covering real
Chatflow, Workflow, Agent, database read/write, plugin tool, knowledge base, file
processing, triggered integration, branching, and loop scenarios.

One important detail: most public DSL examples were exported from older Dify
versions. A small newer sample now includes `0.6.0`, but the corpus is still
mostly legacy. For that reason, this project uses Dify's official source code as
the authority for new `0.6.0` DSL generation, while using the public DSL corpus
as practical reference material for compatibility, graph structure, trigger
workflows, and tool-node patterns.

中文说明见 [README_CN.md](./README_CN.md).

## Follow Silicon Scout S01 On WeChat

Welcome to follow my WeChat Official Account: **硅基斥候 S01 (Silicon
Scout S01)**. The account is still just getting started, so if this skill helps
you, a follow would mean a lot. I will keep sharing practical skills I
personally find useful, plus AI news, knowledge, and notes.

**Recon focus**

Silicon Scout S01 follows large language models, AI agents, AI coding and
toolchains, hands-on product tests, enterprise and government AI adoption, and
policy, security, and compliance.

**Why "Scout"?**

A scout enters unknown territory first, checks what is real, and brings back
useful intelligence.

In the AI context, S01 does that by personally testing new models, tools, and
products, checking their risk boundaries, and explaining the actionable
takeaways clearly.

My other open-source projects will also be announced on this account first.

<img src="./assets/wechat-official-account.jpg" alt="WeChat Official Account QR code for Silicon Scout S01" width="220">

**Current release: V2.0.** The earlier version was effectively V1.0: it
established the import-ready Dify DSL baseline. V2.0 adds deeper real-world YAML
learning, business use-case routing, and Agent Skills specification alignment.

## Why This Exists

Dify workflows are powerful, but DSL authoring is easy to get wrong:

- `version` must be a string.
- Graph edges must point to real node IDs.
- Tool nodes need exact provider/plugin/tool identity fields.
- Database tools need safe SQL parameter binding.
- New plugin tools need exported schemas or plugin metadata.

This skill collects Dify DSL structure, node schemas, real exported examples,
database read/write patterns, plugin marketplace guidance, and a local validator
into one reusable package.

For new workflows, the skill defaults to `version: "0.6.0"`, the current version
declared by Dify source. Older public DSLs are still valuable, but they are not
treated as the latest schema authority.

For new app creation, the skill defaults to Dify `workflow` mode. It switches or
offers `advanced-chat` when the user needs Chatflow behavior such as multi-turn
memory, `sys.query`, chat file upload, or `answer` nodes.

## V2.0 Update Notes

V1.0 focused on making the agent able to write valid, import-ready Dify DSL:
official `0.6.0` structure, node schemas, graph wiring, plugin dependencies,
database tool patterns, and a local validator.

V2.0 goes further: it teaches the agent how to choose the right workflow shape
for a business request, not only how to fill YAML fields.

- Expanded the public YAML corpus from 172 to 262 parseable Dify app DSL files.
- Studied three additional sources:
  `TheOneWithChair/Dify-DSL-generator`,
  `g-krishna0/dify-export-test`, and
  `Petrus-Han/dify-usecase-playground`.
- Added a default mode strategy: create `workflow` by default, and use
  `advanced-chat` only when Chatflow behavior is needed.
- Added `references/usecase-node-selection.md` to map business needs to modes,
  triggers, node patterns, and reliability rules.
- Added stronger guidance for schedule, webhook, plugin-trigger, Slack, Feishu,
  email, GitHub sync, document extraction, form validation, RAG, and reusable
  workflow-tool scenarios.
- Updated the validator so trigger-based side-effect workflows without `end`
  produce a precise warning instead of a generic terminal-node warning.
- Checked the skill against the Agent Skills specification and Anthropic's public
  skills examples; the install payload is now limited to the files the skill
  actually uses.

V2.0 still targets official Dify app DSL `version: "0.6.0"` for new generation.
Public examples are used as real-world design evidence, not as the source of
truth for the latest schema.

## Installation

Clone this repository, then run the installer for your agent platform:

```bash
git clone https://github.com/yzmw123/dify-workflow-dsl-skill.git
cd dify-workflow-dsl-skill
bash install.sh --platform codex
```



Other platforms:

```bash
# Claude Code
bash install.sh --platform claude

# Codex
bash install.sh --platform codex

# OpenClaw
bash install.sh --platform openclaw

# Hermes
bash install.sh --platform hermes

# OpenCode
bash install.sh --platform opencode
```

Install to all supported default locations:

```bash
bash install.sh --platform all
```

If your agent uses a different skills directory, pass it explicitly:

```bash
bash install.sh --platform codex --target-dir "$HOME/.codex/skills/dify-workflow-dsl"
```

The installer is intentionally simple: it copies `SKILL.md`, `references/`,
`scripts/`, and metadata into the target skills directory. Re-run with `--force`
to overwrite a previous installation.

For OpenCode, the default target is the official global skills directory:
`$HOME/.config/opencode/skills/dify-workflow-dsl`. Set `OPENCODE_CONFIG_DIR` or
use `--target-dir` if your OpenCode config lives elsewhere.

## What It Can Do

- Generate import-ready `workflow` and `advanced-chat` Dify DSL YAML.
- Recommend `workflow` vs `advanced-chat` and choose node patterns from business
  requirements.
- Target official Dify app DSL `version: "0.6.0"` for new files.
- Create common nodes: Start, End, Answer, LLM, Code, IF/ELSE, HTTP Request,
  Template Transform, Variable Aggregator, Assigner, Document Extractor,
  Question Classifier, Parameter Extractor, Knowledge Retrieval, Agent,
  Iteration, Loop, Tool, Datasource, trigger nodes, and more.
- Wire graph edges and branch handles correctly.
- Add marketplace, package, and GitHub plugin dependencies.
- Build database read/write workflows with PostgreSQL tools, including patterns
  for `spance/db_client_node` and `hjlarry/database`.
- Review existing DSL files for import risks and behavioral bugs.
- Validate YAML with `scripts/validate_dsl.py`.

## Key Advantage

This skill turns Dify workflow creation into a requirements-writing task.

You can say something like:

```text
Create a Dify Chatflow where users upload a financial report, extract the text,
summarize it, write the parsed result into PostgreSQL, and later answer questions
by reading the right document record from the database.
```

The agent can then produce the YAML structure, nodes, edges, tool parameters,
database SQL, and validation notes. That is the liberation: less canvas clicking,
less copy-paste, fewer invisible import mistakes.

## How To Use

Place this folder in your Codex skills directory or invoke it explicitly when
asking the agent to work on a Dify DSL.

Example prompt:

```text
Use $dify-workflow-dsl to create an advanced-chat Dify workflow.
Users can upload a PDF, extract text, summarize it with Qwen, insert the summary
and raw text into PostgreSQL, and answer the user after the insert succeeds.
```

For editing an existing DSL:

```text
Use $dify-workflow-dsl to review this Dify YAML and fix any import-breaking
issues. Pay special attention to tool nodes and database SQL.
```

For a new plugin tool:

```text
Use $dify-workflow-dsl to add the GitHub plugin search tool.
I have exported a minimal Dify DSL containing that tool node; use it as the schema
source and adapt it into my workflow.
```

## Recommended Workflow For New Plugin Tools

The safest way to support a tool that is not already in the examples:

1. In Dify, create a minimal workflow.
2. Add and configure the target tool node once.
3. Export the DSL.
4. Give that exported YAML to the agent.
5. Let the agent reuse the exact `provider_id`, `tool_name`, `paramSchemas`,
   `tool_parameters`, and dependency fields.

Reliability levels:

- Minimal exported DSL from your workspace: highest confidence.
- Plugin source repo or `.difypkg`: high confidence.
- Marketplace page only: medium confidence.
- Tool name only: draft only, not guaranteed.

## Validation

Run:

```bash
python3 scripts/validate_dsl.py path/to/workflow.yml
```

Validate multiple DSL files:

```bash
python3 scripts/validate_dsl.py examples/*.yml
```

The validator checks YAML parsing, string DSL version, graph edge references,
node type consistency, LLM/tool basics, variable references, and common SQL
mistakes such as trailing commas in `INSERT` column lists.

## Project Structure

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
├── assets/
│   └── wechat-official-account.jpg
├── install.sh
├── references/
│   ├── complete-examples.md
│   ├── database-tools.md
│   ├── dsl-structure.md
│   ├── node-schemas.md
│   ├── official-0.6-target.md
│   ├── plugin-marketplace-tools.md
│   ├── real-world-yml-study.md
│   └── usecase-node-selection.md
├── scripts/
│   └── validate_dsl.py
├── README.md
└── README_CN.md
```

## Maintenance Guide

Keep this skill useful by updating it when Dify changes:

- Check the current DSL version in Dify source.
- Keep the official target reference separate from old public sample notes.
- Export minimal DSLs for new node types and plugin tools.
- Periodically sample real public DSLs, especially from active repositories, and
  fold repeated patterns back into `references/`.
- Add stable patterns to `references/`, not to `SKILL.md`.
- Keep `SKILL.md` short so the agent loads only the essential workflow.
- Add deterministic checks to `scripts/validate_dsl.py` when repeated import
  errors are discovered.
- Re-run skill validation after edits:

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py .
python3 scripts/validate_dsl.py path/to/workflow.yml
```

## Limitations

- A generated DSL may still need import testing inside your Dify workspace.
- Plugin authorization is usually stored in Dify, not in DSL.
- A marketplace page alone may not expose enough schema detail to guarantee a
  tool node will work.
- LLM-generated SQL should be treated carefully; prefer fixed parameterized SQL
  whenever possible.
- Dify versions, plugin versions, and exported schemas can change over time.

## Acknowledgements

This project references Dify's official open-source implementation and selected
public Dify DSL/workflow examples. Special thanks to:

- Dify: https://github.com/langgenius/dify
- DifyAIA: https://github.com/BannyLon/DifyAIA
- Awesome-Dify-Workflow: https://github.com/svcvit/Awesome-Dify-Workflow
- dify-for-dsl: https://github.com/wwwzhouhui/dify-for-dsl
- Dify DSL generator: https://github.com/TheOneWithChair/Dify-DSL-generator
- dify-export-test: https://github.com/g-krishna0/dify-export-test
- dify-usecase-playground: https://github.com/Petrus-Han/dify-usecase-playground
- Agent Skills specification: https://agentskills.io/specification
- Anthropic skills examples: https://github.com/anthropics/skills

## Useful Links

- Dify: https://github.com/langgenius/dify
- Dify Marketplace: https://marketplace.dify.ai/
- Dify official plugins: https://github.com/langgenius/dify-official-plugins
- Dify marketplace plugin index: https://github.com/langgenius/dify-plugins
