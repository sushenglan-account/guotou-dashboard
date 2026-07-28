---
name: use-cc-model
description: >
  当用户说"使用cc模型"、"切换到cc模型"、"启用cc模型"、"调用cc模型"、"切到cc"、
  "换cc模型"或类似含义时，通过百度 Comate OneAPI 平台调用 Claude Sonnet 4.6 API
  替代当前默认模型（通常是千帆 GLM-5）来回答问题。
  
  cc = Claude Sonnet 4.6，用户可能用缩写"cc"、"CC"、"claude"、"sonnet"或"claude sonnet"
  指代同一个模型。
  
  使用此技能的场景：
  - 用户明确说"使用cc模型"
  - 用户说"切换到claude"、"用claude回答"
  - 用户说"切到sonnet"、"用sonnet模型"
  - 用户提到"不用glm了，用cc"
  
  本技能仅负责通过 curl/requests 直接调用 API，不走 DuMate 默认模型中转。
---

# 使用 CC 模型（Claude Sonnet 4.6）

## 触发条件

当用户说以下任意一种方式时触发：
- "使用cc模型"
- "切换到cc模型"
- "启用cc模型"
- "调用cc模型"
- "切到cc"
- "换cc模型"
- "用claude回答"
- "切换到claude"
- "用sonnet模型"
- "不用glm了，用cc"

## 调用方式

使用 HTTP 直接调用 Claude Sonnet 4.6 API（通过百度 OneAPI 平台）：

```
POST https://oneapi-comate.baidu-int.com/v1/messages
Authorization: Bearer sk-w4ENEt8TfHvdBcYpD5411c8a173a41CfAb9404AbB5DeAdA6
anthropic-version: 2023-06-01
Content-Type: application/json
```

请求体：
```json
{
  "model": "Claude Sonnet 4.6",
  "messages": [
    {"role": "user", "content": "用户的原始问题"}
  ],
  "max_tokens": 4000
}
```

## 工作流程

1. 提取用户说"使用cc模型"之后（或当轮对话中）提出的实际问题
2. 将问题作为 `content` 字段内容
3. 通过 curl 或 python requests 调用 API
4. 将 Claude 的回复直接返回给用户，不做修改

## 注意事项

- 此调用**不走 DuMate 默认模型**，而是直接访问 OneAPI 端点
- 请求格式是 Anthropic 原生格式（`/v1/messages`），不是 OpenAI 兼容格式
- 用户的 API Key 已配置：`sk-w4ENEt8TfHvdBcYpD5411c8a173a41CfAb9404AbB5DeAdA6`
- 单次回复 `max_tokens` 默认 4000，如需更长可调整为 64000（模型上限）
- 如果 API 调用失败，返回错误信息给用户，不要静默 fallback 到 GLM
