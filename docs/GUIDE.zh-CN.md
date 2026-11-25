# Dify Claude Code 插件：安装、测试与上架说明

状态：v0.5.5 原型，尚未提交任何官方目录。

## 一、插件能做什么

用户在 Claude Code 里描述需求，插件就在他的 Dify 工作区里把应用建好、测好、发布好，**全程不用打开 Dify 控制台**。Cloud 和自部署都支持，插件会自己判断走哪条路，用户不用选。

| 命令 | 作用 |
| --- | --- |
| `/dify:setup` | 连接 Dify：探测服务器，自动选路，登录，选工作区 |
| `/dify:new-app <需求>` | 需求 → spec → 生成应用 → 导入 → 草稿测试 → 经你同意后发布、给出 Web App 链接。API Key 在路径 B 自动建；路径 A 上如果 difyctl 没有建 Key 的命令，插件会告诉你在网页哪里建，并让你在终端里保存 |
| `/dify:test-app` | 用 Service API 对已发布应用跑验收用例、看日志 |
| `/dify:knowledge` | 把本地文件建成知识库，测试召回 |
| `/dify:connect-app` | 把已发布应用接成 Claude Code 可调用的工具（应用自带的 MCP 服务） |
| `/dify:doctor` | 自检：difyctl 版本、走哪条路、是否登录、当前工作区、可用模型、已存的 Key（打码），并列出要修的问题 |
| `difyctl` skill | Dify 官方 difyctl skill，原样打包 |

> **要在自己电脑上的 Claude Code 里用。** 如果在云端会话里装（网页版 Claude Code，或从桌面、手机 App 开的云端会话），插件跑在远程沙盒里，看不到你电脑上的 difyctl、登录状态和本机的 Dify，只能连 Dify Cloud 或有公网地址的 Dify。`/dify:setup` 和 `/dify:doctor` 检测到云端会话时会先直接说明，不会再让你重新登录。

## 二、两条路是怎么自动选的

`/dify:setup` 会先访问服务器上两个不需要登录的地址：

- `/openapi/v1/_version` 返回 200：服务器开了官方接口 → **路径 A：difyctl**（默认）。**Dify Cloud 已经开了**；自部署和企业版从 **1.20 起默认也开着**（`OPENAPI_ENABLED` 默认 `true`），所以社区版 1.20 默认就走这条；1.19 要手动设 `OPENAPI_ENABLED=true`。插件给你一个链接和一个设备码，你在平时用的浏览器里（已经登录 Dify 的那个）点一次“授权”，之后全部由 difyctl 完成。企业版还支持 SSO 授权。在 CI 或没有浏览器的机器上，可以在自己的终端里设好 `DIFY_SERVER` 和 `DIFY_TOKEN`，插件会跳过登录。difyctl 安装的是最新版，命令由服务器的目录（catalog）下发，不需要和服务器版本对齐。
- 否则 → **路径 B：控制台接口**（备用，只给 1.19 及更早、或者手动关了官方接口的自部署）。插件打开一个临时浏览器窗口，进入 Dify 登录页，用户正常登录。

路径 B 的细节：

- **浏览器登录（默认）**：插件用你电脑上的 Chrome / Edge / Brave / Chromium 打开一个临时窗口，进入 Dify 登录页。你用任何方式登录都可以，验证码、Google、GitHub、SSO 都行，人机验证也是你本人在浏览器里过的。登录成功后，插件只取走会话 cookie 并关闭窗口。窗口用的是一次性配置，不会碰你平时用的浏览器和里面的登录状态。会话存在 `~/.config/dify-claude-plugin/`，只有你自己能读，过期了会自动续期。
- 备用方式：自部署服务器如果开着密码或验证码登录，又没有桌面环境（比如远程服务器），可以在自己的终端里用 `--method password` 或 `--method email-code` 登录。
- 风险：控制台接口是 Dify 网页自用的内部接口，没有兼容性承诺，Dify 升级后可能需要跟着改。服务器一旦打开 `/openapi/v1`，插件会自动切到路径 A。

路径 B 复用了 `yaxuanm/dify-ce-workflow-autobuilder-skill` 里的控制台调用（导入和确认、草稿运行和解析事件、发布、开启 API、创建 API Key），只把原来 `docker exec` 读 `SECRET_KEY` 自签 JWT 的登录换成了账号登录，所以远程自部署也能用。

工作区里没有可用的大模型时（新装的自部署一定会遇到，Cloud 试用额度用完也会），`/dify:setup` 和 `/dify:new-app` 会先停下来告诉用户，问他有哪家的 Key（OpenAI、Anthropic、Gemini、DeepSeek、通义、智谱、Moonshot、Azure，或者自建的兼容接口）。路径 A 上，插件找到对应的模型插件，**先问用户再安装**，然后给用户一条命令在他自己的终端里运行：输入 Key 时不显示，直接交给 difyctl 保存，不经过聊天、不写文件。路径 B 上，插件给出这台服务器的模型供应商页面地址（`<服务器>/integrations/model-provider`），用户在页面里填。

## 三、本地安装测试

```bash
cd ~/Fluffy/dify-claude-plugin
claude --plugin-dir .            # 不安装，直接加载
# 或者按真实用户的方式安装：
claude plugin marketplace add ~/Fluffy/dify-claude-plugin
claude plugin install dify@dify-plugins
```

推到 GitHub 之后，用户安装命令是 `/plugin marketplace add yaxuanm/dify-claude-plugin`，再 `/plugin install dify@dify-plugins`。

也可以让 Agent 自己装：对它说「按 https://raw.githubusercontent.com/yaxuanm/dify-claude-plugin/main/docs/install-for-agents.md 安装 Dify 插件」。它会装插件和 difyctl（下载前先问你），然后让你运行 `/dify:setup`。这个链接要等仓库推到 GitHub 后才能用。

### 分版本测试

社区版、Cloud、企业版各测一遍。每个版本都先运行下面这条命令，看插件选了哪条路，再按表格逐项测。

```bash
python3 scripts/dify_console.py detect <服务器地址>
```

输出里的 `path` 是 `difyctl` 就是路径 A（官方接口），是 `console` 就是路径 B（临时浏览器窗口登录）。

#### 1. 社区版（本地 Docker）

从 1.20 起社区版默认就开了官方接口（`OPENAPI_ENABLED` 默认 `true`），1.19 默认是关的。要测两轮：

- **第一轮，官方接口开着**（1.20 默认，或 1.19 手动打开）：`detect` 应该返回 `path: difyctl`。
- **第二轮，官方接口关掉**：在 `docker/.env` 里设 `OPENAPI_ENABLED=false`（1.19 不设就是关的），用 `docker compose up -d` 重建容器（普通 restart 不会重新读环境文件），再 `detect`，应该返回 `path: console`。
- **可选，个人访问令牌**（1.20+）：在 Dify 的“账号”页建一个令牌，在你自己的终端里设 `DIFY_SERVER` 和 `DIFY_TOKEN` 再启动 Claude Code，`/dify:setup` 应该不用登录直接认出账号。

服务器地址一般是 `http://localhost`（看你 Docker 映射的端口）。第一次打开要先在浏览器里建管理员账号，并在“设置 → 模型供应商”里配一个模型，这两步插件替代不了。

#### 2. Dify Cloud

服务器选 `https://cloud.dify.ai`。`detect` 应该返回 `path: difyctl`。登录是设备码：Claude 给链接和码，你在平时登录 Dify 的浏览器里点“授权”。

#### 3. 企业版

服务器填企业版的控制台地址。

- 如果服务器开了官方接口，`detect` 返回 `path: difyctl`。登录时设备码授权页会跳到公司的 SSO，用公司账号登录后点“授权”（企业版 PR #584 加的 SSO 设备授权）。
- 如果返回 `path: console`，说明这台没开 `OPENAPI_ENABLED`。临时浏览器窗口里同样可以走 SSO 登录，但更建议请管理员打开官方接口再测。
- 额外检查：只能看到自己有权限的工作区；没有编辑权限的账号导入应用时，应该收到清楚的权限报错，而不是莫名失败。

#### 每个版本都要测的项目

| 命令 | 怎么测 | 通过标准 |
| --- | --- | --- |
| `/dify:setup` | 按提示登录 | Claude 说明走哪条路且和 `detect` 一致；最后显示你的邮箱和工作区；全程没让你在聊天里输入密码或 token |
| `/dify:new-app` | `一个工作流：输入客户反馈，输出情绪（正面/负面/中性）和一句话摘要` | 先给 spec 等你确认；用的是工作区里真实存在的模型；导入成功并给出应用 ID；草稿测试逐条给结果；发布前一定先问你；同意后给 Web App 链接；路径 B 建好 API Key 只显示别名，路径 A 告诉你去网页哪里建 Key |
| `/dify:test-app` | 对上一步发布的应用跑用例 | 每条用例都有通过 / 不通过和理由；有失败时能读到失败的节点并给出改法 |
| `/dify:knowledge` | 选 2 到 3 个本地 Markdown 或 PDF | 上传前列出文件和大小并等你确认；索引状态最后是 `completed`；3 个测试问题能召回对应文档 |
| `/dify:connect-app` | 把发布的应用接成工具 | `claude mcp list` 里能看到 `dify-<应用名>`；在 Claude Code 里调用它能拿到应用的回答 |

每一项都请记下三件事：是否需要打开 Dify 控制台（以及在哪一步）、报错原文、大概耗时。目前已知两处可能还要进控制台：`/dify:knowledge` 的知识库 API Key 和 `/dify:connect-app` 的 MCP 地址在路径 A 上还没有 difyctl 命令可以拿到，这正是这轮要确认的。

### 校验命令

```bash
claude plugin validate . --profile directory --strict
```

## 四、已验证和未验证

已验证：

- 目录提交检查（`--profile directory --strict`）通过，没有警告。
- `validate_dsl.py` 用 Dify 仓库里 36 个真实 DSL 跑过，没有误报。
- 浏览器登录在本地 Chromium 上测过：打开登录页、等待登录、取 cookie、关闭窗口、清理临时配置都正常。
- `dify_console.py` 在模拟服务器上跑通了整套流程：探测、登录（cookie 和 CSRF）、access token 过期后自动续期、查模型、导入（含版本确认）、草稿运行和用例测试、发布、建 API Key 并存进本机 key 库、Web App 链接、登出。
- 让 Claude 端到端跑了一遍 `/dify:new-app`：它查了模型、写了 spec 和用例、生成 DSL 并校验、导入、跑了草稿测试。测试没通过时，它停在发布前，并指出是服务器的问题。这是对的：模拟服务器对任何输入都返回同一个结果。

未验证（需要你用真实账号测）：

- **以上所有调用都没有在真实的 Dify Cloud 或自部署上跑过。** 请求格式取自 Dify 当前源码和你仓库里在 CE 上验证过的脚本，但字段细节可能还要调整。
- difyctl 在 Cloud 上的设备码登录和整套流程（Cloud 的 `/openapi/v1` 已确认打开，difyctl v1.19.0 已随 Dify 1.19.0 发布，和 Cloud 版本一致）。
- 控制台备用路径在真实自部署上的 cookie 和接口细节。
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
- [ ] **许可证**：本仓库用 Apache-2.0。复制进来的 difyctl skill 来自 langgenius/dify，该仓库是“修改版 Apache 2.0”（Dify Open Source License），需要确认可以这样再分发。另一个做法是插件不带这份 skill，改成在 setup 时执行 `difyctl install skills ~/.claude/skills`，用 difyctl 内置的版本，和二进制永远一致；代价是没装 difyctl 之前插件里看不到它，也不会出现在插件目录的 skill 列表里。现在两份内容和 dify 主干完全一致。
- [ ] **difyctl 正式发布**：difyctl 已经随 Dify 1.17.1 起的 Release 发布（最新 v1.19.0，有 macOS / Linux / Windows 包）。需要确认它在 Cloud 上是对外支持的功能，而不只是内部开着。
- [ ] **控制台备用路径**：只在没开官方接口的自部署上用，用的是控制台内部接口。提交前让 Dify 后端确认可以保留，或者正式版去掉，只留 difyctl。
- [ ] **维护人**：上游 skill 更新时同步、改版本号、处理 issue。

## 五、后续可以加的

- 模型供应商 API Key 也通过终端录入（控制台接口支持），彻底不进控制台。
- Codex 版：同一套 skills，加 `.codex-plugin/plugin.json` 和 `.agents/plugins/marketplace.json`。
- 你仓库里的 New Agent / Agent V2 能力，等接口在 Cloud 上可用后合进来。
- 用 `claude plugin eval` 给 setup / new-app 加评测用例。
