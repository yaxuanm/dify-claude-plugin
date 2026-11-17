# Dify Claude Code 插件：安装、测试与上架说明

状态：v0.3.2 原型，尚未提交任何官方目录。

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

- `/openapi/v1/_version` 返回 200：服务器开了官方接口 → **路径 A：difyctl**（默认）。**Dify Cloud 已经开了**（你查到 `{"version":"1.19.0","edition":"CLOUD"}`），自部署和企业版设了 `OPENAPI_ENABLED=true` 也走这条。插件给你一个链接和一个设备码，你在平时用的浏览器里（已经登录 Dify 的那个）点一次“授权”，之后全部由 difyctl 完成。企业版还支持 SSO 授权。
- 否则 → **路径 B：控制台接口**（备用，只给没开官方接口的自部署或旧版本）。插件打开一个临时浏览器窗口，进入 Dify 登录页，用户正常登录。

路径 B 的细节：

- **浏览器登录（默认）**：插件用你电脑上的 Chrome / Edge / Brave / Chromium 打开一个临时窗口，进入 Dify 登录页。你用任何方式登录都可以，验证码、Google、GitHub、SSO 都行，人机验证也是你本人在浏览器里过的。登录成功后，插件只取走会话 cookie 并关闭窗口。窗口用的是一次性配置，不会碰你平时用的浏览器和里面的登录状态。会话存在 `~/.config/dify-claude-plugin/`，只有你自己能读，过期了会自动续期。
- 备用方式：自部署服务器如果开着密码或验证码登录，又没有桌面环境（比如远程服务器），可以在自己的终端里用 `--method password` 或 `--method email-code` 登录。
- 风险：控制台接口是 Dify 网页自用的内部接口，没有兼容性承诺，Dify 升级后可能需要跟着改。服务器一旦打开 `/openapi/v1`，插件会自动切到路径 A。

路径 B 复用了 `yaxuanm/dify-ce-workflow-autobuilder-skill` 里的控制台调用（导入和确认、草稿运行和解析事件、发布、开启 API、创建 API Key），只把原来 `docker exec` 读 `SECRET_KEY` 自签 JWT 的登录换成了账号登录，所以远程自部署也能用。

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

1. 在 Claude Code 里运行 `/dify:setup`，服务器选 Dify Cloud。Claude 应该说明会走 difyctl（官方接口），没装 difyctl 时先问你要不要装。
2. Claude 给出一个链接和设备码。在你平时的浏览器里打开链接，确认设备码，点“授权”，然后回 Claude Code 说“好了”。
3. Claude 显示你的账号和工作区。
4. 运行 `/dify:new-app 一个工作流：输入客户反馈，输出情绪（正面/负面/中性）和一句话摘要`。依次检查：先给 spec 让你确认；导入后给出 app_id；跑草稿测试并给出逐条结果；发布前一定问你；同意后返回 Web App 链接和 API Key 别名（Key 本身不显示）。
5. 在 Dify 控制台里核对一下（只是验收，正常使用时不需要）：应用已存在、已发布、API Key 已创建。
6. 记录每一步的耗时和卡点。

### 验收步骤（自部署）

同上，服务器填你的地址。开了 `OPENAPI_ENABLED=true` 的服务器和 Cloud 一样走 difyctl；没开的会弹出临时浏览器窗口让你登录（需要 Chrome / Edge / Brave）。

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
- [ ] **许可证**：本仓库用 Apache-2.0。复制进来的 difyctl skill 来自 langgenius/dify，该仓库是“修改版 Apache 2.0”（Dify Open Source License），需要确认可以这样再分发，或者改成安装时再执行 `difyctl install skills`。
- [ ] **difyctl 正式发布**：difyctl 已经随 Dify 1.17.1 起的 Release 发布（最新 v1.19.0，有 macOS / Linux / Windows 包）。需要确认它在 Cloud 上是对外支持的功能，而不只是内部开着。
- [ ] **控制台备用路径**：只在没开官方接口的自部署上用，用的是控制台内部接口。提交前让 Dify 后端确认可以保留，或者正式版去掉，只留 difyctl。
- [ ] **维护人**：上游 skill 更新时同步、改版本号、处理 issue。

## 五、后续可以加的

- 模型供应商 API Key 也通过终端录入（控制台接口支持），彻底不进控制台。
- Codex 版：同一套 skills，加 `.codex-plugin/plugin.json` 和 `.agents/plugins/marketplace.json`。
- 你仓库里的 New Agent / Agent V2 能力，等接口在 Cloud 上可用后合进来。
- 用 `claude plugin eval` 给 setup / new-app 加评测用例。
