# DuMate 切换 Claude 模型的经验总结

> 本文档记录通过 OneAPI 聚合平台在 DuMate/opencode 环境中接入 Claude 系列模型的完整经验，已去除敏感信息（API Key、具体接口地址）。
> 适用场景：DuMate 免费版固定使用 GLM-5，需要通过自定义 Provider 接入其他模型。

---

## 一、问题背景

### 1.1 环境限制

DuMate 免费版默认通过千帆个人配额代理调用 **GLM-5**，无法通过 UI 切换模型。当需要更强的编程/推理能力时，需通过以下方式绕过：

- **方案 A**：升级 DuMate 订阅（如支持）
- **方案 B**：在 `opencode.json` 配置自定义 Provider（推荐）
- **方案 C**：直接调用外部 API（curl/python），不走 DuMate 模型层

### 1.2 配置文件的覆盖问题

DuMate 桌面端每次重启会话时，会**重新生成** `opencode.json`，覆盖手动修改的内容。因此：
- 直接编辑 `opencode.json` 仅在当前会话有效
- 持久化方案需要找到 DuMate 不覆盖的配置入口（如环境变量、UI 设置）
- 或者创建 **Skill**，通过触发词直接调用外部 API

---

## 二、OneAPI 平台接入 Claude 的核心要点

### 2.1 平台特性

OneAPI 是模型聚合平台，将多个厂商的 API 统一封装为 OpenAI 兼容格式或原生格式。接入时需注意：

| 特性 | 说明 |
|------|------|
| 统一鉴权 | 一个 API Key 可访问多个模型 |
| 渠道分组 | 不同模型可能分属不同渠道，部分模型可能未开通 |
| 格式差异 | Claude 可能同时支持 OpenAI 兼容格式和 Anthropic 原生格式，但**仅原生格式可用** |

### 2.2 关键发现：Claude 模型必须用 Anthropic 原生格式

经过多次测试，发现：

- **OpenAI 兼容端点**（`/v1/chat/completions`）→ 返回 404 或"无可用渠道"
- **Anthropic 原生端点**（`/v1/messages`）→ 正常返回

这意味着：
1. OneAPI 平台的 Claude 模型**只暴露了原生格式**
2. 配置 Provider 时，`npm` 包必须选 `@ai-sdk/anthropic` 而非 `@ai-sdk/openai-compatible`
3. 请求头必须包含 `anthropic-version: 2023-06-01`

### 2.3 请求格式对比

**错误格式（OpenAI 兼容）**：
```
POST /v1/chat/completions
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "model": "Claude Sonnet 4.6",
  "messages": [{"role": "user", "content": "..."}]
}
```

**正确格式（Anthropic 原生）**：
```
POST /v1/messages
Authorization: Bearer {api_key}
anthropic-version: 2023-06-01
Content-Type: application/json

{
  "model": "Claude Sonnet 4.6",
  "messages": [{"role": "user", "content": "..."}],
  "max_tokens": 4000
}
```

**关键区别**：
- 端点从 `/v1/chat/completions` 变为 `/v1/messages`
- 新增 `anthropic-version` 请求头（必需）
- `max_tokens` 在 Anthropic 格式中是必填项

---

## 三、模型 ID 格式陷阱

### 3.1 列表显示的 vs 实际可用的

通过 `/v1/models` 查询到的模型 ID 可能与实际调用所需的不一致：

| 列表显示 | 实际调用（OpenAI 格式） | 实际调用（Anthropic 格式） |
|---------|----------------------|------------------------|
| `Claude Sonnet 4.6` | `claude-sonnet-4-6`（不可用） | `Claude Sonnet 4.6`（可用） |
| `Claude Opus 4.7` | `claude-opus-4-7`（不可用） | 待验证 |

**经验**：列表中的模型 ID 含空格，而 Anthropic 原生格式恰好需要这种带空格的 ID。OpenAI 兼容格式下的各种变体（连字符、下划线、小写）均返回"无可用渠道"。

### 3.2 验证可用性的方法

在正式配置前，先用 curl 验证：

```bash
curl -s {base_url}/v1/models \
  -H "Authorization: Bearer {api_key}" \
  -H "Accept: application/vnd.github+json"
```

然后对每个目标模型，用原生格式测试：

```bash
curl -s {base_url}/v1/messages \
  -H "Authorization: Bearer {api_key}" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"Claude Sonnet 4.6","messages":[{"role":"user","content":"hi"}],"max_tokens":100}'
```

---

## 四、DuMate/opencode 中的配置方案

### 4.1 方案一：临时配置 opencode.json（单次会话）

编辑 `config/opencode/opencode.json`，添加自定义 Provider：

```json
{
  "model": "OneAPI/Claude Sonnet 4.6",
  "provider": {
    "OneAPI": {
      "npm": "@ai-sdk/anthropic",
      "name": "OneAPI",
      "options": {
        "baseURL": "{oneapi_base_url}/v1",
        "apiKey": "{api_key}"
      },
      "models": {
        "Claude Sonnet 4.6": {
          "name": "Claude Sonnet 4.6",
          "limit": {
            "context": 200000,
            "output": 64000
          }
        }
      }
    }
  }
}
```

**注意**：`npm` 字段必须填 `@ai-sdk/anthropic`，而不是 `@ai-sdk/openai-compatible`。

**限制**：DuMate 重启后此配置会被覆盖，仅适合临时测试。

### 4.2 方案二：创建 Skill（持久化）

在 `skills/user/` 下创建 Skill 目录，编写 `SKILL.md`，通过触发词直接调用 API：

**触发词设计**：
- 明确触发词："使用cc模型"、"切换到cc"、"用claude回答"
- 模糊触发词："不用glm了"、"换模型"

**Skill 核心逻辑**：
1. 提取用户实际问题内容
2. 构造 Anthropic 原生格式的请求体
3. 通过 curl/python requests 调用 `/v1/messages`
4. 将返回内容直接呈现给用户

**优势**：
- 不依赖 opencode.json 配置
- DuMate 重启后仍然可用
- 可在不同会话中复用

### 4.3 方案三：环境变量或全局配置（需 DuMate 支持）

如果 DuMate 桌面端支持读取环境变量配置模型，可通过以下方式持久化：

```bash
export OPENCODE_DEFAULT_MODEL="OneAPI/Claude Sonnet 4.6"
export OPENCODE_PROVIDER_ONEAPI_BASEURL="{base_url}"
export OPENCODE_PROVIDER_ONEAPI_APIKEY="{api_key}"
```

**当前状态**：DuMate 免费版暂不支持此方式，需关注后续版本更新。

---

## 五、Node.js 版本兼容性

安装 `@ai-sdk/anthropic` 时可能遇到版本警告：

```
npm WARN EBADENGINE Unsupported engine {
  package: '@ai-sdk/provider-utils@5.0.7',
  required: { node: '>=22' },
  current: { node: 'v18.19.1', npm: '9.2.0' }
}
```

**处理方式**：
- 忽略警告，继续安装（通常功能正常）
- 如需彻底解决，升级 Node.js 到 v22+
- 或者通过 nvm 临时切换 Node 版本

---

## 六、常见问题与排查

### 6.1 "无可用渠道"

**原因**：
- 模型 ID 格式错误（OpenAI 兼容格式的 ID 不被接受）
- 该模型在 OneAPI 平台未开通上游渠道
- 账户没有该模型的访问权限

**排查**：
1. 确认使用 `/v1/messages` 原生端点
2. 确认模型 ID 与列表显示一致（含空格）
3. 联系平台管理员确认 Claude 渠道是否开通

### 6.2 "bad response status code 404"

**原因**：
- 端点错误（用了 OpenAI 的 `/v1/chat/completions`）
- 缺少 `anthropic-version` 请求头

**解决**：切换到 `/v1/messages` 端点，并添加 `anthropic-version: 2023-06-01`。

### 6.3 "Resource not accessible by personal access token"

**原因**：Token 权限不足，缺少 `contents:write` 或其他权限。

**解决**：在平台重新生成 Token，确保包含所需的 Repository/API 权限。

### 6.4 配置被重置

**原因**：DuMate 桌面端每次重启会话会重新生成 `opencode.json`。

**解决**：使用 Skill 方案（方案二），或等待 DuMate 开放持久化配置入口。

---

## 七、安全注意事项

1. **API Key 管理**：
   - 绝不将 Key 硬编码在公开仓库中
   - 使用环境变量或配置文件（加入 `.gitignore`）
   - 定期轮换 Key，特别是 Fine-grained Token

2. **Token 权限最小化**：
   - 仅授予需要的权限（Contents:Read/Write）
   - 不要给 Token 超出必要的 scope
   - Fine-grained Token 优于 Classic Token（权限可控）

3. **传输安全**：
   - 确保使用 HTTPS
   - 避免在日志中打印完整 Key
   - 本地配置文件中存储 Key 时，注意文件权限

---

## 八、模型能力对比参考

| 模型 | 上下文窗口 | 输出上限 | 适用场景 | 通过 OneAPI 可用性 |
|------|-----------|---------|---------|----------------|
| GLM-5 | 192K | 128K | 通用中文对话 | ✅ 默认 |
| Claude Sonnet 4.6 | 200K | 64K | 编程、推理、分析 | ✅ 需原生格式 |
| Claude Opus 4.7 | 200K | 64K | 复杂推理、Agent | 待验证 |
| DeepSeek-V4-Pro | - | - | 编程、数学 | ✅ |
| GPT-5.5 | - | - | 通用多语言 | ✅ |

---

## 九、推荐实践

1. **先测试，再配置**：用 curl 直接验证 API 可用性，确认无误后再写配置
2. **保留默认模型**：配置中保留原有 GLM-5 Provider，方便随时切换回默认
3. **Skill 优先**：对于需要跨会话持久化的模型切换需求，使用 Skill 方案
4. **文档化**：将配置过程记录到知识库，方便团队复用和排查
5. **监控用量**：注意 Claude 系列模型的 token 消耗较高（特别是长上下文场景）

---

## 附录：相关术语

| 术语 | 说明 |
|------|------|
| OneAPI | 模型聚合平台，统一封装多厂商 API |
| Anthropic 原生格式 | Claude 的原始 API 格式，端点 `/v1/messages` |
| OpenAI 兼容格式 | 模拟 OpenAI 接口规范的格式，端点 `/v1/chat/completions` |
| Fine-grained Token | GitHub 细粒度权限 Token，按权限范围精确控制 |
| Skill | DuMate/opencode 的插件技能，通过触发词执行特定任务 |
| Provider | opencode 中的模型供应商配置，包含 baseURL、apiKey、模型列表等 |

---

*文档版本: v1.0*
*最后更新: 2026-07-13*
