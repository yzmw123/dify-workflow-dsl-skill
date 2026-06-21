# Dify Workflow DSL Skill

**Dify Workflow DSL Skill** 是一套帮助 AI Agent 编写、修改、审查和调试
Dify 工作流 DSL YAML 的技能包。目标很直接：让你用自然语言描述需求，
AI 自动生成可以导入 Dify 的工作流文件。

这个项目的起点很朴素：我发现 Dify 自己搭工作流虽然强大，但真的很麻烦。
拖节点、连线、配工具、调参数、反复试错，时间很容易被消耗在画布操作上。
后来我发现 Dify 工作流支持 YAML 导入导出，也就是产品里说的 DSL。于是我
产生了一个想法：既然工作流可以被写成结构化 YAML，为什么不让 AI 学会
怎么写 Dify 工作流呢？

所以我让 AI 学习了 Dify 的开源代码、自己导出的 DSL，以及 GitHub 上公开
的 Dify 工作流 DSL 示例，并把这些规律整理成了这个 skill。

当前 skill 的目标版本是 Dify 官方源码声明的 app DSL `0.6.0`。在整理过程中，
我系统学习了 Dify 官方源码、自己的导出文件，以及多个公开 DSL 示例仓库。
这些公开仓库一共提供了 262 个可解析的 Dify app DSL，覆盖了 Chatflow、
Workflow、Agent、数据库读写、插件工具、知识库、文件处理、触发器集成、
分支、循环等大量真实场景。

需要说明的是，公开仓库里的 DSL 大多来自旧版本 Dify。新的样本中已经出现
少量 `0.6.0` 导出，但整体仍以旧版为主。因此，本项目以 Dify 官方源码作为
新 DSL 生成的权威依据，同时把这些公开 DSL 作为旧版本兼容性、真实图结构、
触发器工作流和工具节点写法的参考。

English version: [README.md](./README.md)

## 欢迎关注微信公众号

欢迎关注我的微信公众号：**硅基斥候 S01**。目前账号刚起步，如果觉得这个
skill 对你有帮助，请帮我涨个粉丝。我会持续发布自己亲测后觉得好用的
skill，以及 AI 相关的资讯和知识。

**侦查方向**

硅基斥候 S01 关注大语言模型、AI Agent、AI 编程与工具链、产品实测、政企
AI 落地，以及政策、安全与合规。

**为什么叫斥候？**

斥候先进入未知区域探虚实，再把有用的情报带回来。

放到 AI 语境里，S01 做的就是亲测新模型、新工具和新产品，核对风险边界，
把可行动的判断说清楚。

我自己开源的其他项目也会第一时间在公众号公布。

<img src="./assets/wechat-official-account.jpg" alt="硅基斥候 S01 微信公众号二维码" width="220">

**当前版本：V2.0。** 之前的版本可以视为 V1.0：它解决的是“让 Agent 能写出
可导入 Dify 的 DSL”这个基础问题。V2.0 在此基础上继续强化真实 YAML 学习、
业务场景判断，以及 Agent Skills 规范对齐。

## 它解决什么问题

Dify 工作流很强，但手工搭建和手写 DSL 都容易踩坑：

- `version` 必须是字符串。
- 节点 ID 和边连接必须完全对得上。
- 分支节点的 `sourceHandle` 必须匹配 case/class ID。
- Tool 节点必须写对插件、provider、tool name、参数和依赖。
- 数据库读写节点必须注意 SQL 参数绑定和语法细节。
- 新插件工具不能只凭名字瞎猜 schema。

这个 skill 把 Dify DSL 结构、常见节点 schema、真实导出案例、数据库读写
模式、插件市场工具规则和本地校验脚本整理成了一套可复用规范。

新生成的工作流默认使用 `version: "0.6.0"`。公开仓库里的旧版 DSL 仍然很有
价值，但不会被当作最新版 schema 的权威来源。

新建应用时，skill 默认按 Dify `workflow` 模式生成；当用户需要多轮对话、
记忆、`sys.query`、聊天文件上传或 `answer` 节点时，再切换或建议
`advanced-chat`。

## V2.0 更新说明

V1.0 的重点是让 Agent 能写出可导入、结构正确的 Dify DSL：官方 `0.6.0`
结构、节点 schema、图连接、插件依赖、数据库工具模式，以及本地校验脚本。

V2.0 的重点更进一步：不只是会填 YAML 字段，而是让 Agent 更懂“用户这个
业务需求适合什么模式、什么触发方式、什么节点组合”。

- 公开 YAML 学习语料从 172 个可解析 Dify app DSL 扩展到 262 个。
- 新增学习了三个来源：
  `TheOneWithChair/Dify-DSL-generator`、
  `g-krishna0/dify-export-test`、
  `Petrus-Han/dify-usecase-playground`。
- 明确默认模式策略：新建应用默认生成 `workflow`；只有需要 Chatflow 行为时，
  才使用 `advanced-chat`。
- 新增 `references/usecase-node-selection.md`，把业务需求映射到模式选择、
  触发器、节点模式和可靠性规则。
- 强化了定时触发、Webhook、插件事件、Slack、飞书、邮件、GitHub 同步、
  文档提取、表单校验、RAG、复用工作流工具等场景的经验。
- 更新校验脚本：触发器类 side-effect workflow 没有 `end` 时，会给出更准确
  的提醒，而不是泛泛提示缺少终止节点。
- 对照 Agent Skills specification 和 Anthropic 官方 skills 示例检查结构；
  安装脚本现在只复制 skill 真正需要的文件，保持安装目录更精简。

V2.0 仍然默认面向官方 Dify app DSL `version: "0.6.0"`。公开样例用于学习
真实业务图结构和兼容性经验，不作为最新版 schema 的唯一权威来源。

## 安装

克隆仓库后，按你使用的 Agent 平台安装：

```bash
git clone https://github.com/yzmw123/dify-workflow-dsl-skill.git
cd dify-workflow-dsl-skill
bash install.sh --platform codex
```



多平台命令：

```bash
# Claude Code
bash install.sh --platform claude

# Codex
bash install.sh --platform codex

# OpenClaw
bash install.sh --platform openclaw

# Hermes
bash install.sh --platform hermes
```

安装到所有默认支持的平台目录：

```bash
bash install.sh --platform all
```

如果你的 Agent skills 目录不是默认路径，可以手动指定：

```bash
bash install.sh --platform codex --target-dir "$HOME/.codex/skills/dify-workflow-dsl"
```

这个安装脚本的原理很简单：根据 `--platform` 判断目标 skills 目录，然后把
`SKILL.md`、`references/`、`scripts/` 和元数据复制过去。如果已经安装过，
可以加 `--force` 覆盖。

## 最大优势

它把 Dify 工作流搭建从“拖节点、连线、调参数、排查导入错误”变成了
“描述需求”。

你可以直接说：

```text
帮我做一个 Dify Chatflow：用户上传财务报表，系统提取文本，生成摘要，
把原文和结构化结果写入 PostgreSQL；之后用户提问时，先从数据库读取相关
文档，再回答问题。
```

AI 就可以基于这个 skill 生成 YAML、节点、边、工具参数、数据库 SQL 和校验
说明。它的核心价值就是解放重复搭建工作，把精力放回流程设计和业务逻辑。

## 能做什么

- 生成可导入 Dify 的 `workflow` 和 `advanced-chat` DSL YAML。
- 根据业务需求判断应该用 `workflow` 还是 `advanced-chat`，并选择合适节点组合。
- 新文件默认面向官方 Dify app DSL `version: "0.6.0"`。
- 编写常见节点：Start、End、Answer、LLM、Code、IF/ELSE、HTTP Request、
  Template Transform、Variable Aggregator、Assigner、Document Extractor、
  Question Classifier、Parameter Extractor、Knowledge Retrieval、Agent、
  Iteration、Loop、Tool、Datasource、Trigger 等。
- 自动规划节点 ID、边连接和分支 handle。
- 补齐 marketplace、package、GitHub 插件依赖。
- 编写数据库读取、写入、查重、NL2SQL 查询流程。
- 支持 `spance/db_client_node` 和 `hjlarry/database` 两类数据库工具模式。
- 审查已有 DSL 的导入风险和逻辑问题。
- 用 `scripts/validate_dsl.py` 做基础结构校验。

## 怎么用

把这个目录放到你的 Codex skills 目录，或者在提问时显式调用：

```text
Use $dify-workflow-dsl to create an advanced-chat Dify workflow.
用户上传 PDF 后，提取文本，用通义千问总结，然后写入 PostgreSQL，
最后回复用户写入成功和摘要。
```

修改已有 DSL：

```text
Use $dify-workflow-dsl to review this Dify YAML and fix import-breaking issues.
重点检查 tool 节点、数据库 SQL、节点边连接。
```

新增插件工具：

```text
Use $dify-workflow-dsl to add a new Dify marketplace tool.
我已经导出了一个只包含这个工具节点的最小 DSL，请用它作为 schema 来源。
```

## 新插件工具的推荐流程

如果某个工具在示例里没有出现过，最稳的方法是：

1. 在 Dify 里新建一个最小工作流。
2. 拖入目标工具节点，并配置一次可用参数。
3. 导出 DSL。
4. 把这个 YAML 给 AI。
5. AI 复用里面的 `provider_id`、`tool_name`、`paramSchemas`、
   `tool_parameters`、`plugin_unique_identifier` 和 `dependencies`。

可靠性分级：

- 你自己 Dify 工作区导出的最小 DSL：最高可靠。
- 插件源码仓库或 `.difypkg` 包：较高可靠。
- 只有插件市场页面：中等可靠。
- 只有工具名字：只能生成草稿，不能保证导入即用。

## 校验

校验单个 DSL：

```bash
python3 scripts/validate_dsl.py path/to/workflow.yml
```

批量校验多个 DSL：

```bash
python3 scripts/validate_dsl.py examples/*.yml
```

校验脚本会检查 YAML 解析、DSL version 类型、图连接、节点类型、LLM/tool
基础字段、变量引用，以及 `INSERT` 字段列表尾逗号等常见 SQL 问题。

## 项目结构

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

## 后续怎么维护

- Dify 升级后，先确认官方源码里的当前 DSL 版本。
- 把官方目标版本规则和公开旧样本笔记分开维护，避免旧 DSL 反向污染新版本生成。
- 新节点、新插件、新工具，优先导出最小 DSL，再沉淀到 `references/`。
- 定期抽样真实公开 DSL，尤其是活跃仓库里的新案例，把反复出现的模式补回
  `references/`。
- `SKILL.md` 保持短小，只放核心流程和导航。
- 复杂 schema、数据库模板、插件规则放到 `references/`。
- 遇到重复导入错误，就把可自动检查的部分补进 `scripts/validate_dsl.py`。
- 每次更新后运行：

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py .
python3 scripts/validate_dsl.py path/to/workflow.yml
```

## 限制

- 生成的 DSL 仍建议在 Dify 测试工作区导入跑一次。
- 插件授权通常保存在 Dify，不会完整写在 DSL 里。
- 只有插件市场页面时，可能拿不到完整参数 schema，不能 100% 保证工具节点可用。
- LLM 生成 SQL 有风险，能用固定参数化 SQL 时优先固定 SQL。
- Dify 版本、插件版本、导出 schema 都可能变化，需要持续维护。

## 致谢

这个项目参考了 Dify 官方开源实现，以及部分公开的 Dify DSL / 工作流示例。
特别感谢：

- Dify: https://github.com/langgenius/dify
- DifyAIA: https://github.com/BannyLon/DifyAIA
- Awesome-Dify-Workflow: https://github.com/svcvit/Awesome-Dify-Workflow
- dify-for-dsl: https://github.com/wwwzhouhui/dify-for-dsl
- Dify DSL generator: https://github.com/TheOneWithChair/Dify-DSL-generator
- dify-export-test: https://github.com/g-krishna0/dify-export-test
- dify-usecase-playground: https://github.com/Petrus-Han/dify-usecase-playground
- Agent Skills specification: https://agentskills.io/specification
- Anthropic skills examples: https://github.com/anthropics/skills

## 相关链接

- Dify: https://github.com/langgenius/dify
- Dify Marketplace: https://marketplace.dify.ai/
- Dify official plugins: https://github.com/langgenius/dify-official-plugins
- Dify marketplace plugin index: https://github.com/langgenius/dify-plugins
