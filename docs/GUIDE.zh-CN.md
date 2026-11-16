# Dify Claude Code 插件：安装测试与上架说明

状态：v0.1.0 原型，尚未提交任何官方目录。

## 一、插件里有什么

| 组件 | 作用 |
| --- | --- |
| `/dify:setup` | 引导连接：检查并安装 difyctl，用浏览器设备码登录 Dify Cloud 或自部署服务器，选定 workspace。 |
| `/dify:new-app <需求描述>` | 从一句话需求到可运行应用：简短 spec、计划、搭建、跑验收用例，经用户同意后发布并给出 Web App 链接。 |
| `difyctl` skill | 原样打包 Dify 官方 difyctl skill（来自 langgenius/dify 的 `skills/difyctl`），负责具体操作方法。 |

设计取舍：

- 底层用 difyctl，而不是自己写 MCP。difyctl 的命令来自服务器发布的操作目录，Dify 新增能力后插件不用改。Dify 目前没有面向“管理 workspace / 搭应用”的官方远程 MCP，以后如果有，可以在 `plugin.json` 里加 `mcpServers`，体验会更接近 n8n（安装时填 URL，OAuth 授权）。
- 没有加 hooks。n8n 用 SessionStart / PreToolUse hooks 做提醒；我们先保持最小权限，减少审核风险。另外 OpenAI 的插件目录明确不收带生命周期 hooks 的插件，以后做 Codex 版也能复用同一套内容。
- 官方 difyctl skill 是复制进来的，用 `scripts/sync-difyctl-skill.sh` 同步上游，`NOTICE` 记录了来源 commit。

## 二、本地安装测试

前提：已装 Claude Code；有一个 Dify 账号（Cloud 或自部署）。

### 方式 A：不安装，直接加载目录（开发时最快）

```bash
cd ~/Fluffy/dify-claude-plugin
claude --plugin-dir .
```

进入会话后输入 `/dify:setup`。

### 方式 B：按真实用户的方式安装（推荐验收用）

```bash
claude plugin marketplace add ~/Fluffy/dify-claude-plugin
claude plugin install dify@dify-plugins
```

推到 GitHub 之后，用户的安装命令就变成：

```text
/plugin marketplace add yaxuanm/dify-claude-plugin
/plugin install dify@dify-plugins
```

### 校验

```bash
claude plugin validate . --profile directory --strict   # 目录提交前的检查
claude plugin details dify@dify-plugins                  # 看组件和 token 开销
```

### 建议的验收脚本（测“安装 → 连接 → 首个应用跑通”）

1. `/dify:setup`：确认会先问是否安装 difyctl、问服务器地址；给出链接和设备码后停下等你批准；回复“done”后能显示账号和 workspace。
2. `/dify:new-app 一个客服机器人，根据我们的退款政策回答问题，用客户的语言回复`：确认会先出 spec 让你确认，再出计划，再搭建和测试，发布前一定问你。
3. 记录每一步耗时和卡点：difyctl 安装、登录、模型凭证缺失（新 workspace 很常见）、发布。这就是给 Jerome 的转化漏斗数据。

## 三、已验证和未验证

已验证（在云端沙箱里）：

- `claude plugin validate . --profile directory --strict` 通过，没有任何警告。
- 以 marketplace 方式安装成功，3 个 skill 都被识别，常驻开销约 330 tokens。
- 运行 `/dify:setup` 时，Claude 正确调用了插件里的状态脚本，发现没装 difyctl 后先征求同意并询问服务器，没有擅自安装。

未验证，需要你在本机测：

- difyctl 的实际下载安装：沙箱网络访问不到 langgenius/dify 的 GitHub Release API。
- 登录和搭建：需要真实的 Dify 账号。尤其要确认 **Dify Cloud（cloud.dify.ai）是否已支持 difyctl 的设备码登录**，以及 Cloud 当前版本是否带 difyctl 需要的操作目录。如果 Cloud 还不支持，第一版应先面向自部署/企业版用户。

## 四、提交官方目录还需要什么

Claude Code 有三层分发，别混在一起说：

1. **自有 marketplace（现在就能用）**：仓库里有 `.claude-plugin/marketplace.json` 就算发布了，用户 `/plugin marketplace add <owner>/<repo>` 后安装。n8n 目前就是这种方式。
2. **社区目录 `claude-community`**（仓库 anthropics/claude-plugins-community）：通过表单提交。个人作者用 <https://platform.claude.com/plugins/submit>；Team / Enterprise 组织用 <https://claude.ai/admin-settings/directory/submissions/plugins/new>（需要 Directory 权限）。上架通常锁定到某个 commit。
3. **官方目录 `claude-plugins-official`**：Claude Code 文档说它不通过上述表单收录，要通过 Anthropic 的合作伙伴联系人沟通；而该仓库 README 写的是第三方合作伙伴可以用提交表单（<https://clau.de/plugin-directory-submission>）。两个说法不一致，建议 Dify 走合作伙伴渠道问清楚。

需要 Dify 公司提供或确认的事项：

- [ ] **仓库归属**：正式版应放在 Dify 官方 GitHub 组织下（例如 `langgenius/dify-claude-plugin`），然后把 `plugin.json` / README 里的 `yaxuanm` 链接改过去。现在用你的账号做原型。
- [ ] **发布者身份**：`author` 和 marketplace `owner` 现在写的是 “Dify”。从个人仓库对外发布时，这样写可能被视为冒用品牌，正式提交前需要公司授权，或者先改成你的名字。
- [ ] **提交账号**：用 Dify 公司的 Claude Team / Enterprise 组织提交，或由公司指定的人用个人作者入口提交；如果要进官方目录，需要 Anthropic 的合作伙伴联系人。
- [ ] **品牌素材**：`assets/icon.png` 现在是用 Dify 仓库里的 logo.svg 渲染的 512×512 图，需要品牌团队确认或替换。
- [ ] **法务链接**：确认 `privacyPolicyUrl`（https://dify.ai/privacy）、`termsOfServiceUrl`（https://dify.ai/terms）、`supportUrl`、`documentationUrl` 都是正确的公开地址。
- [ ] **许可证**：本仓库用 Apache-2.0。复制进来的 difyctl skill 来自 langgenius/dify，该仓库是“修改版 Apache 2.0”（Dify Open Source License），需要确认可以这样再分发，或者改成安装时再执行 `difyctl install skills`。
- [ ] **difyctl 正式发布**：确认 difyctl 已经随 Dify Release 稳定发布，并支持 Cloud 和主流自部署版本，否则用户装完插件也走不通。
- [ ] **维护人**：上游 skill 更新时同步、改版本号、处理 issue。

## 五、后续可以加的

- Codex 版：同一套 skills，加 `.codex-plugin/plugin.json`（按 OpenAI 要求加 `interface` 字段：displayName、shortDescription、logo、composerIcon、capabilities 等）和 `.agents/plugins/marketplace.json`。
- 如果 Dify 推出官方远程 MCP（OAuth），在 `plugin.json` 里加 `mcpServers` 和 `userConfig`（服务器 URL），安装时直接连接。
- 用 `claude plugin eval` 给 setup / new-app 加评测用例，作为每次发布前的回归测试。
