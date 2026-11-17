# Dify Claude Code 插件：安装、测试与上架说明

状态：v0.3.0 原型，尚未提交任何官方目录。

## 一、插件能做什么

用户在 Claude Code 里描述需求，插件就在他的 Dify 工作区里把应用建好、测好、发布好，**全程不用打开 Dify 控制台**。Cloud 和自部署都支持，插件会自己判断走哪条路，用户不用选。

| 命令 | 作用 |
| --- | --- |
| `/dify:setup` | 连接 Dify：探测服务器，自动选路，登录，选工作区 |
| `/dify:new-app <需求>` | 需求 → spec → 生成应用 → 导入 → 草稿测试 → 经你同意后发布、给出 Web App 链接、建 API Key |
| `/dify:build-dsl <需求>` | 只生成 DSL 文件并离线校验（不想登录时用） |
| `/dify:test-app` | 用 Service API 对已发布应用跑验收用例、看日志 |
| `/dify:knowledge` | 把本地文件建成知识库，测试召回 |
| `/dify:connect-app` | 把已发布应用接成 Claude Code 可调用的工具（应用自带的 MCP 服务） |
| `difyctl` skill | Dify 官方 difyctl skill，原样打包 |

## 二、两条路是怎么自动选的

`/dify:setup` 会先访问服务器上两个不需要登录的地址：

- `/openapi/v1/_version` 返回 200：服务器开了官方接口（`OPENAPI_ENABLED=true`）→ **路径 A：difyctl**。浏览器授权页点一次“授权”即可，之后全部由 difyctl 完成。
- 否则 → **路径 B：控制台接口**（目前 Dify Cloud 都走这条）。用户在自己的终端里运行一次登录命令，输入邮箱和密码。

路径 B 的细节：

- 只支持**邮箱 + 密码**登录。Cloud 的邮箱验证码在发送前强制要求 Cloudflare 人机验证（源码 `EmailCodeSendPayload`："Required at runtime for Dify Cloud"），命令行无法通过，插件也不会绕过。Google / GitHub 登录需要浏览器跳转，同样不支持。
- 用验证码或 Google 注册、没设过密码的账号：在 Dify 里点头像 → 账号 → “设置密码”，设一次即可。
- 密码只在用户自己的终端输入，不显示、不保存、不经过聊天；保存的只有会话 cookie，位置是 `~/.config/dify-claude-plugin/`（仅本人可读）。会话过期会自动续期。
- 自部署但没开官方接口时，也走路径 B；如果服务器允许，可以用邮箱验证码登录（`--method email-code`）。
- 风险：控制台接口是 Dify 网页自用的内部接口，没有兼容性承诺，Dify 升级后可能需要跟着改。Cloud 一旦打开 `/openapi/v1`，插件会自动切到路径 A。

路径 B 复用了 `yaxuanm/dify-ce-workflow-autobuilder-skill` 里的控制台调用（导入和确认、草稿运行和解析事件、发布、开启 API、创建 API Key），只把原来 `docker exec` 读 `SECRET_KEY` 自签 JWT 的登录换成了账号登录，所以 Cloud 和远程自部署都能用。

唯一可能还要进一次控制台的情况：工作区里一个可用的大模型都没有。这时需要先在“设置 → 模型供应商”里填 API Key。Cloud 新账号自带试用额度，一般不会遇到。

## 三、本地安装测试

```bash
cd ~/Fluffy/dify-claude-plugin
claude --plugin-dir .            # 不安装，直接加载
# 或者按真实用户的方式安装：
claude plugin marketplace add ~/Fluffy/dify-claude-plugin
claude plugin install dify@dify-plugins
```

推到 GitHub 之后，用户安装命令是 `/plugin marketplace add yaxuanm/dify-claude-plugin`，再 `/plugin install dify@dify-plugins`。

### 验收步骤（Cloud）

1. 浏览器打开 <https://cloud.dify.ai/console/api/system-features>，确认 `enable_email_password_login` 是 `true`。
2. 确认你的 Cloud 账号设置过密码。
3. 在 Claude Code 里运行 `/dify:setup`，服务器选 Dify Cloud。Claude 应该说明会走“控制台登录”，并给你一条登录命令。
4. 另开一个终端运行这条命令，输入邮箱和密码，回到 Claude Code 回复“done”。Claude 应该显示你的账号和工作区。
5. 运行 `/dify:new-app 一个工作流：输入客户反馈，输出情绪（正面/负面/中性）和一句话摘要`。依次检查：先给 spec 让你确认；导入后给出 app_id；跑草稿测试并给出逐条结果；发布前一定问你；同意后返回 Web App 链接和 API Key 别名（Key 本身不显示）。
6. 在 Dify 控制台里核对一下（只是验收，正常使用时不需要）：应用已存在、已发布、API Key 已创建。
7. 记录每一步的耗时和卡点。

### 验收步骤（自部署）

同上，服务器填你的地址。开了 `OPENAPI_ENABLED=true` 的服务器会走 difyctl 路径（需要授权页点一次）；没开的走控制台路径。

### 校验命令

```bash
claude plugin validate . --profile directory --strict
```

## 四、已验证和未验证

已验证：

- 目录提交检查（`--profile directory --strict`）通过，没有警告。
- `validate_dsl.py` 用 Dify 仓库里 36 个真实 DSL 跑过，没有误报。
- `dify_console.py` 在模拟服务器上跑通了整套流程：探测、终端密码登录（cookie 和 CSRF）、access token 过期后自动续期、查模型、导入（含版本确认）、草稿运行和用例测试、发布、建 API Key 并存进本机 key 库、Web App 链接、登出。
- 让 Claude 端到端跑了一遍 `/dify:new-app`：它查了模型、写了 spec 和用例、生成 DSL 并校验、导入、跑了草稿测试。测试没通过时，它停在发布前，并指出是服务器的问题。这是对的：模拟服务器对任何输入都返回同一个结果。

未验证（需要你用真实账号测）：

- **以上所有调用都没有在真实的 Dify Cloud 或自部署上跑过。** 请求格式取自 Dify 当前源码和你仓库里在 CE 上验证过的脚本，但字段细节可能还要调整。
- Cloud 是否开着密码登录、Cloud 登录后的 cookie 名称和域名是否和源码一致。
- difyctl 的真实下载和设备码登录。
- 知识库文件上传。

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
- [ ] **控制台登录的审核风险**：Cloud 路径用的是控制台内部接口和密码登录。提交前最好让 Dify 后端确认这种用法可以接受，并在 Anthropic 审核时说明：发布方就是 Dify 本身，凭证只在用户本机终端输入。长期还是建议 Cloud 打开官方 `/openapi/v1`，插件会自动切过去。
- [ ] **维护人**：上游 skill 更新时同步、改版本号、处理 issue。

## 五、后续可以加的

- 模型供应商 API Key 也通过终端录入（控制台接口支持），彻底不进控制台。
- Codex 版：同一套 skills，加 `.codex-plugin/plugin.json` 和 `.agents/plugins/marketplace.json`。
- 你仓库里的 New Agent / Agent V2 能力，等接口在 Cloud 上可用后合进来。
- 用 `claude plugin eval` 给 setup / new-app 加评测用例。
