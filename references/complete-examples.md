# Dify DSL 完整示例

These graph examples target new generated DSL with `version: "0.7.0"`. Model provider
and plugin dependency identifiers are placeholders unless copied from a real
workspace export; replace them with exact exported identifiers before production
import.

## Contents

- 简单翻译工作流 (`workflow`)
- IF/ELSE 条件分支 (`workflow`)
- HTTP + 代码处理 (`workflow`)
- Chatflow 多轮对话 (`advanced-chat`)

## 1. 简单翻译工作流 (workflow 模式)

```yaml
app:
  name: "中英翻译"
  description: "将中文翻译成英文"
  icon: "🌐"
  icon_type: emoji
  icon_background: "#E4FBCC"
  mode: workflow
  use_icon_as_answer_icon: false
kind: app
version: "0.7.0"
dependencies: []
workflow:
  conversation_variables: []
  environment_variables: []
  features:
    file_upload:
      image:
        enabled: false
      enabled: false
    opening_statement: ""
    retriever_resource:
      enabled: false
    sensitive_word_avoidance:
      enabled: false
    speech_to_text:
      enabled: false
    suggested_questions: []
    suggested_questions_after_answer:
      enabled: false
    text_to_speech:
      enabled: false
  graph:
    edges:
    - data:
        isInIteration: false
        sourceType: start
        targetType: llm
      id: 1000001-source-1000002-target
      source: "1000001"
      sourceHandle: source
      target: "1000002"
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        sourceType: llm
        targetType: end
      id: 1000002-source-1000003-target
      source: "1000002"
      sourceHandle: source
      target: "1000003"
      targetHandle: target
      type: custom
      zIndex: 0
    nodes:
    - data:
        title: "开始"
        type: start
        variables:
          - label: "中文文本"
            variable: chinese_text
            type: paragraph
            required: true
            max_length: 5000
      height: 120
      id: "1000001"
      position: { x: 30, y: 300 }
      positionAbsolute: { x: 30, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "翻译"
        type: llm
        model:
          provider: deepseek
          name: deepseek-chat
          mode: chat
          completion_params:
            temperature: 0.3
        prompt_template:
          - id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            role: system
            text: "你是一个专业的中英翻译。只输出翻译结果，不要解释。"
          - id: "b2c3d4e5-f6a7-8901-bcde-f12345678901"
            role: user
            text: "请将以下中文翻译成英文：\n\n{{#1000001.chinese_text#}}"
        context:
          enabled: false
          variable_selector: []
        variables: []
        vision:
          enabled: false
        selected: false
      height: 98
      id: "1000002"
      position: { x: 334, y: 300 }
      positionAbsolute: { x: 334, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "结束"
        type: end
        outputs:
          - value_selector: ["1000002", text]
            variable: translation
          - value_selector: ["1000001", chinese_text]
            variable: original
      height: 90
      id: "1000003"
      position: { x: 638, y: 300 }
      positionAbsolute: { x: 638, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    viewport: { x: 50, y: 200, zoom: 0.8 }
```

---

## 2. IF/ELSE 条件分支 (workflow 模式)

```yaml
app:
  name: "内容分类处理"
  description: "根据内容类型选择不同处理方式"
  icon: "🔀"
  icon_type: emoji
  icon_background: "#D1E9FF"
  mode: workflow
  use_icon_as_answer_icon: false
kind: app
version: "0.7.0"
dependencies: []
workflow:
  conversation_variables: []
  environment_variables: []
  features:
    file_upload:
      image:
        enabled: false
      enabled: false
    opening_statement: ""
    retriever_resource:
      enabled: false
    sensitive_word_avoidance:
      enabled: false
    speech_to_text:
      enabled: false
    suggested_questions: []
    suggested_questions_after_answer:
      enabled: false
    text_to_speech:
      enabled: false
  graph:
    edges:
    - data:
        isInIteration: false
        sourceType: start
        targetType: if-else
      id: 2000001-source-2000002-target
      source: "2000001"
      sourceHandle: source
      target: "2000002"
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        sourceType: if-else
        targetType: llm
      id: 2000002-true-2000003-target
      source: "2000002"
      sourceHandle: "true"
      target: "2000003"
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        sourceType: if-else
        targetType: llm
      id: 2000002-false-2000004-target
      source: "2000002"
      sourceHandle: "false"
      target: "2000004"
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        sourceType: llm
        targetType: variable-aggregator
      id: 2000003-source-2000005-target
      source: "2000003"
      sourceHandle: source
      target: "2000005"
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        sourceType: llm
        targetType: variable-aggregator
      id: 2000004-source-2000005-target
      source: "2000004"
      sourceHandle: source
      target: "2000005"
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        sourceType: variable-aggregator
        targetType: end
      id: 2000005-source-2000006-target
      source: "2000005"
      sourceHandle: source
      target: "2000006"
      targetHandle: target
      type: custom
      zIndex: 0
    nodes:
    - data:
        title: "开始"
        type: start
        variables:
          - label: "输入内容"
            variable: content
            type: paragraph
            required: true
            max_length: 10000
      height: 120
      id: "2000001"
      position: { x: 30, y: 300 }
      positionAbsolute: { x: 30, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "是否含代码"
        type: if-else
        cases:
          - case_id: "true"
            conditions:
              - comparison_operator: contains
                id: "cond-001"
                value: "```"
                varType: string
                variable_selector: ["2000001", content]
            id: "true"
            logical_operator: and
        conditions:
          - comparison_operator: contains
            id: "cond-001"
            value: "```"
            variable_selector: ["2000001", content]
        logical_operator: and
        desc: ""
      height: 126
      id: "2000002"
      position: { x: 334, y: 300 }
      positionAbsolute: { x: 334, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "代码分析"
        type: llm
        model:
          provider: deepseek
          name: deepseek-chat
          mode: chat
          completion_params:
            temperature: 0.3
        prompt_template:
          - id: "p1"
            role: user
            text: "分析以下代码：\n\n{{#2000001.content#}}"
        context:
          enabled: false
          variable_selector: []
        variables: []
        vision:
          enabled: false
        selected: false
      height: 98
      id: "2000003"
      position: { x: 638, y: 200 }
      positionAbsolute: { x: 638, y: 200 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "文本分析"
        type: llm
        model:
          provider: deepseek
          name: deepseek-chat
          mode: chat
          completion_params:
            temperature: 0.7
        prompt_template:
          - id: "p2"
            role: user
            text: "分析以下文本：\n\n{{#2000001.content#}}"
        context:
          enabled: false
          variable_selector: []
        variables: []
        vision:
          enabled: false
        selected: false
      height: 98
      id: "2000004"
      position: { x: 638, y: 400 }
      positionAbsolute: { x: 638, y: 400 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "汇总结果"
        type: variable-aggregator
        output_type: string
        variables:
          - ["2000003", text]
          - ["2000004", text]
        advanced_settings:
          group_enabled: false
      height: 80
      id: "2000005"
      position: { x: 942, y: 300 }
      positionAbsolute: { x: 942, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "结束"
        type: end
        outputs:
          - value_selector: ["2000005", output]
            variable: result
      height: 90
      id: "2000006"
      position: { x: 1246, y: 300 }
      positionAbsolute: { x: 1246, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    viewport: { x: 50, y: 150, zoom: 0.7 }
```

---

## 3. HTTP + 代码处理 (workflow 模式)

```yaml
app:
  name: "天气查询"
  description: "获取天气数据并格式化"
  icon: "🌤"
  icon_type: emoji
  icon_background: "#E4FBCC"
  mode: workflow
  use_icon_as_answer_icon: false
kind: app
version: "0.7.0"
dependencies: []
workflow:
  conversation_variables: []
  environment_variables: []
  features:
    file_upload:
      image:
        enabled: false
      enabled: false
    opening_statement: ""
    retriever_resource:
      enabled: false
    sensitive_word_avoidance:
      enabled: false
    speech_to_text:
      enabled: false
    suggested_questions: []
    suggested_questions_after_answer:
      enabled: false
    text_to_speech:
      enabled: false
  graph:
    edges:
    - data:
        isInIteration: false
        sourceType: start
        targetType: http-request
      id: 3000001-source-3000002-target
      source: "3000001"
      sourceHandle: source
      target: "3000002"
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        sourceType: http-request
        targetType: code
      id: 3000002-source-3000003-target
      source: "3000002"
      sourceHandle: source
      target: "3000003"
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        sourceType: code
        targetType: end
      id: 3000003-source-3000004-target
      source: "3000003"
      sourceHandle: source
      target: "3000004"
      targetHandle: target
      type: custom
      zIndex: 0
    nodes:
    - data:
        title: "开始"
        type: start
        variables:
          - label: "城市"
            variable: city
            type: text-input
            required: true
            max_length: 48
      height: 90
      id: "3000001"
      position: { x: 30, y: 300 }
      positionAbsolute: { x: 30, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "获取天气"
        type: http-request
        method: get
        url: "https://wttr.in/{{#3000001.city#}}?format=j1"
        headers: ""
        params: ""
        body:
          type: none
          data: []
        authorization:
          type: no-auth
          config: null
        timeout:
          max_connect_timeout: 10
          max_read_timeout: 30
          max_write_timeout: 30
        variables: []
      height: 110
      id: "3000002"
      position: { x: 334, y: 300 }
      positionAbsolute: { x: 334, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "格式化"
        type: code
        code_language: python3
        code: |
          def main(body: str) -> dict:
              import json
              data = json.loads(body)
              current = data.get("current_condition", [{}])[0]
              result = f"温度: {current.get('temp_C', 'N/A')}°C\n"
              result += f"湿度: {current.get('humidity', 'N/A')}%\n"
              result += f"风速: {current.get('windspeedKmph', 'N/A')} km/h"
              return {"output": result}
        variables:
          - value_selector: ["3000002", body]
            variable: body
        outputs:
          output:
            type: string
            children: null
        desc: ""
      height: 54
      id: "3000003"
      position: { x: 638, y: 300 }
      positionAbsolute: { x: 638, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "结束"
        type: end
        outputs:
          - value_selector: ["3000003", output]
            variable: weather
      height: 90
      id: "3000004"
      position: { x: 942, y: 300 }
      positionAbsolute: { x: 942, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    viewport: { x: 50, y: 200, zoom: 0.8 }
```

---

## 4. Chatflow 多轮对话 (advanced-chat 模式)

```yaml
app:
  name: "旅行助手"
  description: "多轮对话旅行顾问"
  icon: "✈️"
  icon_type: emoji
  icon_background: "#FFEAD5"
  mode: advanced-chat
  use_icon_as_answer_icon: false
kind: app
version: "0.7.0"
dependencies: []
workflow:
  conversation_variables:
    - description: "对话历史"
      id: "cv-001"
      name: History
      selector: [conversation, History]
      value: []
      value_type: array[string]
  environment_variables: []
  features:
    file_upload:
      image:
        enabled: false
      enabled: false
    opening_statement: "你好！我是旅行助手，请告诉我你想去哪里旅行？"
    retriever_resource:
      enabled: false
    sensitive_word_avoidance:
      enabled: false
    speech_to_text:
      enabled: false
    suggested_questions:
      - "推荐一个3天的旅行目的地"
      - "日本旅行需要准备什么？"
    suggested_questions_after_answer:
      enabled: false
    text_to_speech:
      enabled: false
  graph:
    edges:
    - data:
        isInIteration: false
        sourceType: start
        targetType: template-transform
      id: 4000001-source-4000002-target
      source: "4000001"
      sourceHandle: source
      target: "4000002"
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        sourceType: template-transform
        targetType: assigner
      id: 4000002-source-4000003-target
      source: "4000002"
      sourceHandle: source
      target: "4000003"
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        sourceType: assigner
        targetType: agent
      id: 4000003-source-4000004-target
      source: "4000003"
      sourceHandle: source
      target: "4000004"
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        sourceType: agent
        targetType: answer
      id: 4000004-source-answer-target
      source: "4000004"
      sourceHandle: source
      target: answer
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        sourceType: answer
        targetType: template-transform
      id: answer-source-4000005-target
      source: answer
      sourceHandle: source
      target: "4000005"
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        sourceType: template-transform
        targetType: assigner
      id: 4000005-source-4000006-target
      source: "4000005"
      sourceHandle: source
      target: "4000006"
      targetHandle: target
      type: custom
      zIndex: 0
    nodes:
    - data:
        title: "开始"
        type: start
        variables: []
      height: 54
      id: "4000001"
      position: { x: 30, y: 300 }
      positionAbsolute: { x: 30, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "用户消息格式化"
        type: template-transform
        template: "user:{{ user_msg }}"
        variables:
          - value_selector: [sys, query]
            variable: user_msg
      height: 54
      id: "4000002"
      position: { x: 334, y: 300 }
      positionAbsolute: { x: 334, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "追加用户消息"
        type: assigner
        version: "2"
        items:
          - input_type: variable
            operation: append
            value: ["4000002", output]
            variable_selector: [conversation, History]
            write_mode: over-write
      height: 88
      id: "4000003"
      position: { x: 638, y: 300 }
      positionAbsolute: { x: 638, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "旅行顾问"
        type: agent
        agent_strategy_provider_name: langgenius/agent/agent
        agent_strategy_name: function_calling
        agent_strategy_label: FunctionCalling
        plugin_unique_identifier: "langgenius/agent:0.0.4@hash"
        agent_parameters:
          model:
            type: constant
            value:
              mode: chat
              model: gpt-4o-mini
              model_type: llm
              provider: langgenius/openai/openai
              type: model-selector
          query:
            type: constant
            value: "{{#conversation.History#}}"
          instruction:
            type: constant
            value: "你是旅行顾问，为用户规划旅行。"
          tools:
            type: constant
            value:
              - enabled: true
                provider_name: langgenius/duckduckgo/duckduckgo
                tool_name: ddgo_search
                type: builtin
                parameters:
                  max_results: 5
                extra:
                  description: "搜索旅行信息"
          maximum_iterations:
            type: constant
            value: 4
        output_schema: null
        desc: ""
      height: 198
      id: "4000004"
      position: { x: 942, y: 300 }
      positionAbsolute: { x: 942, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "直接回复"
        type: answer
        answer: "{{#4000004.text#}}"
        variables: []
      id: answer
      position: { x: 1246, y: 300 }
      positionAbsolute: { x: 1246, y: 300 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "助手消息格式化"
        type: template-transform
        template: "assistant:{{ assistant_msg }}"
        variables:
          - value_selector: ["4000004", text]
            variable: assistant_msg
      height: 54
      id: "4000005"
      position: { x: 1246, y: 500 }
      positionAbsolute: { x: 1246, y: 500 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    - data:
        title: "追加助手消息"
        type: assigner
        version: "2"
        items:
          - input_type: variable
            operation: append
            value: ["4000005", output]
            variable_selector: [conversation, History]
            write_mode: over-write
      height: 88
      id: "4000006"
      position: { x: 1550, y: 500 }
      positionAbsolute: { x: 1550, y: 500 }
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 244
    viewport: { x: 50, y: 200, zoom: 0.7 }
```
