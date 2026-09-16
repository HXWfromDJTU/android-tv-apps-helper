# v0.4.0-rc.1 HTML 点选测试报告

日期：2026-09-16。基线 main/b7c1c8d；隔离分支 feature/html-choice-20260916153546。未继承或修改并行的账号迁移工作。

## 结论

| 状态 | 范围 | 结果 |
|---|---|---|
| ✅ | 自动化回归 | 162 项通过；含原生旧流程、四桌面 HTML、解压后 CLI、真实 MCP SDK stdio 协议 |
| ✅ | Chrome 浏览器 | 5 项通过；其中 1 项是模拟宿主 iframe，不能视为真实 Agent 内嵌验收 |
| ✅ | Skill / plugin | 元数据校验通过；四平台包共享 HTML、harness、MCP 模块和接口说明 |
| ✅ | 用户三选迁移 | 独立 Agent 在临时 WorkBuddy 旧 session 勾选三项，再迁移到 HTML；三项保留、完整列表可达，提交进入具名下载确认 |
| ✅ | 安装授权边界 | 选应用不触发下载/ADB/安装；等待操作证据后才进入结果，未操作任何真实电视 |
| ❌ | 电脑控制连接 | 首次和重试均返回 native pipe startup failed / nodeRepl.fetch request failed |
| ⚠️ | 客户端真实安装 / 内嵌 | Codex、WorkBuddy、豆包工作本版未能完成，不计通过 |
| ⏭️ | Claude 实机 | 按此前约定暂不验收；Claude Desktop 要求另具本地执行能力，MCP UI 不是 ADB 执行器 |

因此只发布测试版，不替代 v0.3.4 稳定版，不让稳定更新检查自动升级用户。

## 用户反馈与实际修复

| 原问题 | 修复 | 证据 |
|---|---|---|
| 原生选项分页，确认被藏在后面 | 四桌面统一 HTML 完整 checkbox 列表，底部固定「确认所选应用，进入安装流程」 | 实际浏览器视口坐标断言，列表首屏可见 |
| 同题重试退回文字输入 | HTML 当前问题与 token 绑定，失败保留选择，不生成文字编号菜单 | 无选择/旧题/重复/非法输入测试 |
| 多选或刷新丢失选择 | 旧会话 resume-html 保留选择；页面 sessionStorage 保存草稿，草稿不等于批准 | 独立三项迁移与刷新测试 |
| 把内容挤进短标题 | 进度表、阻塞和指引在标题上方，标题简短 | HTML 上下文结构与浏览器渲染 |
| 点完后 Agent 不知道 | MCP ui/message 通知 + tv_ui_wait；浏览器 wait-ui 轮询权威状态 | SDK 状态资源/提交、CLI wait、多轮浏览器测试 |
| ZIP 与内嵌混为一谈 | README 分列 Skill 安装、可选 MCP 注册、浏览器启动与等待 | 独立引导审阅 |

## 红绿回归和独立审查修复

1. 原基线没有 HTML 通道；新增测试先暴露缺失，再实现共享 controller、HTTP 和 MCP。
2. 四进程重复点击最初发生 JSON/临时文件冲突；增加跨进程会话锁后，只接受一份，另外三份判为过期。
3. 审查发现 MCP ui/message 使用对象而客户端要求数组；改为数组并用模拟 iframe 消息检查验证。
4. 审查发现 resume-html / plan-install 未完整覆盖会话锁；补齐写入锁，snapshot 留在锁外避免重入死锁。
5. S0 无问题时误显示「流程已结束」；浏览器测试先失败，修为「等待 Agent 准备当前问题」后通过。
6. 独立用户视角测试发现 CSS sticky 并不保证按钮首屏可见：900×740 视口中按钮底边为 915.5。新增真实坐标断言先失败，改为 fixed 底栏后通过。独立复验：900×740 中 y=683/h=45；400×700 中 y=643/h=45，三项已选时均完整可见。
7. 模拟内嵌宿主自动扩高到 2015px，使确认按钮仍落在长卡片底部；新增高度断言先失败，将内嵌高度建议限制到 700px、列表在页面内滚动后通过。真实宿主是否遵循建议仍待验收。
8. 更新规则补齐 RC → 同版本稳定版的提示、Claude Desktop → Claude 通用包映射，各自先失败后通过。

## 可复现命令

在仓库根目录执行：

```sh
python3 -m unittest discover -s tests -q
python3 tests/browser_html_smoke.py -v
python3 scripts/build_release.py --output-dir dist-v0.4.0-rc.1
(cd dist-v0.4.0-rc.1 && shasum -a 256 -c SHA256SUMS)
```

浏览器测试使用 Python Playwright 和已安装的 Chrome；MCP 集成测试使用官方 Python SDK 1.26.0。SDK 不存在时协议用例会 skip，不能把 skip 算成通过。本机该测试实际执行通过。普通浏览器运行本身只需 Python 标准库。

五项浏览器用例：连续两轮选择并返回待执行动作；完整列表/刷新保留/确认按钮视口内；非法信息重试；未开始不能假完成；模拟 iframe MCP 初始化、资源轮询、点击与数组消息回传。所有设备与应用上下文均为测试 fixture。

解压包检查覆盖四个平台：旧原生多轮回归、初始化 HTML、预检查首题和 wait-ui 状态读取，并比较所有共享核心文件 hash。包存在和 CLI 可执行不代表宿主已经安装或加载 Skill。

## WorkBuddy / 豆包工作 HTML 能力证据

| 平台 | 已获取的证据 | 不能据此宣称的事项 |
|---|---|---|
| WorkBuddy 5.5.6 | 官方 Buddy App 文档列出 MCP Apps；已安装 app.asar 含 MCP App HTML MIME、ui/initialize、tool-result 桥接实现 | 当前账号一定开放该入口；本插件已内嵌显示、成功回调 |
| 豆包工作 2.29.10 | 已安装 ai-views 前端资源含 text/html;profile=mcp-app 的 HTML 读取器及 ui/initialize、ui/message、tool-result 桥接 | 所有发行渠道/账号都支持；本插件已经实际内嵌验收 |
| Codex / Claude Desktop | 适配同一可选 MCP Apps 协议；未渲染时提供浏览器通道 | 仅安装 Skill 就一定得到内嵌 UI |

主要协议来源：[MCP Apps 概览](https://modelcontextprotocol.io/extensions/apps/overview)、[官方类型定义](https://github.com/modelcontextprotocol/ext-apps/blob/main/src/spec.types.ts)、[WorkBuddy Buddy App](https://open.workbuddy.cn/docs/buddy-app)。[腾讯 CodeBuddy MCP Apps 文档](https://www.codebuddy.cn/docs/cli/mcp-apps)用于交叉核对 resourceUri 与回调设计，但不把 CodeBuddy 的能力直接等同为所有 WorkBuddy 版本的能力。

豆包证据来自本机 /Applications/DoubaoWork.app 内 ai-views 的 async/2019.js、24580.js；只做范围内只读检查，未修改客户端资源。未找到可用的官方公开说明不是“不支持”的证明。

## 安全和等待边界

- HTTP 只绑定 127.0.0.1；随机 fragment 凭据、Bearer 校验、严格 Host/Origin、大小限制、无任意文件/命令接口。
- MCP 只允许配置目录内的既有会话；UI 提交工具标记 app-only，不提供 ADB 执行。
- 旧页面 token、重复提交和未选择均拒绝；补充说明仅记录、不批准额外操作。
- MCP 轮询通过只读资源，不通过重复反向 tools/call 读取状态；提交仍服从宿主权限，不能开启 bypass。
- 普通网页不能独立唤醒已结束回合的 Agent。必须保留后台服务与 25 秒有界等待循环，或明确报告宿主限制。
- 没有替换用户实际 Skill、改 MCP 配置、删除客户端数据、连接或修改电视；这些不计为完成。

## 真实客户端待验收清单

Codex、WorkBuddy、豆包分别：备份旧 Skill → 下载校验测试 ZIP → 实际安装版本可见 → 新会话读取新 Skill → 注册/信任本地 MCP（或浏览器回退）→ 自动只读预检查 → 连续两题点击 → 全列表多选三项且确认按钮首屏可见 → 按名称二次确认 → 错误后仍为 HTML → 安全结束。需要真实安装/界面证据后，才可把对应项目改为通过。

测试日志和报告不公开本机 IP、电视序列号、账号、session 内容或带凭据的本地网页 URL。
