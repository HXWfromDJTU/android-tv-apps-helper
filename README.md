# Android TV Apps Helper

一个面向 Codex / ChatGPT Agent 的 Android TV 引导式插件。它把“连电视、选软件、核验 APK、安装、验证、恢复”收敛成可检查的状态机，让用户每轮只回答一个明确问题。

当前版本：`v0.1.0`

## 交互原则

- 每个交互回合只出现一个必答问题，并给出互斥选项。
- 宿主支持表单/选择卡时使用原生 UI；不支持或渲染失败时，原题原选项降级为编号文字菜单。
- 空白、含糊、同时选择多个单选项、回答旧问题或格式错误都不会推进状态；插件会停留在原题。
- 推荐项只标注，不预选。
- 所有 ADB 设备命令绑定已确认的 `serial`。
- 安装前展示不可变计划；设备、文件摘要、命令或风险发生变化时，原批准失效。
- “APK 有效”“已安装”“已启动”“有运行信号”“用户现场验收”分别记录，不混写为“正常”。

## 完整状态流转

```mermaid
flowchart TD
    S0["S0 显示：流程范围与只读/变更边界"] --> Q0{"问题：开始只读检查？<br/>开始 / 查看范围 / 安全退出"}
    Q0 -- 查看范围 --> S0
    Q0 -- 安全退出 --> END0["结果：未执行命令，生成退出记录"]
    Q0 -- 开始 --> S1["S1 结果：ADB 版本或缺失状态"]

    S1 --> D1{ADB 可用？}
    D1 -- 否 --> Q1{"问题：安装 Google 官方 Platform-Tools / 提交绝对路径 / 退出"}
    Q1 -- 提交路径 --> Q1P{"问题：路径: /absolute/path/to/adb"}
    Q1P -- 无效 --> Q1P
    Q1P -- 有效 --> S2
    Q1 -- 安装 --> S2
    Q1 -- 退出 --> END0
    D1 -- 是 --> S2["S2 结果：设备列表、连接状态、发现证据"]

    S2 --> D2{发现几台设备？}
    D2 -- 0 台 --> Q2Z{"问题：检查网络后重扫 / 提交电视 IP / 退出"}
    Q2Z -- 重扫 --> S2
    Q2Z -- 提交 IP --> Q2IP{"问题：IP: 192.168.x.x"}
    Q2IP -- 无效 --> Q2IP
    Q2IP -- 有效 --> S3
    Q2Z -- 退出 --> END0
    D2 -- 多台 --> Q2M{"问题：选择一台设备 / 重扫 / 退出"}
    Q2M -- 设备编号 --> S3
    Q2M -- 重扫 --> S2
    Q2M -- 退出 --> END0
    D2 -- 1 台 --> S3["S3 结果：device / unauthorized / offline / unreachable"]

    S3 --> D3{ADB 状态？}
    D3 -- unauthorized --> Q3U{"问题：已接受电视授权 / 没看到提示 / 重试 / 退出"}
    Q3U -- 已接受或重试 --> S3
    Q3U -- 没提示 --> S2
    Q3U -- 退出 --> END0
    D3 -- offline --> R3["安全重连；不影响其他在线设备"] --> S3
    D3 -- unreachable --> S2
    D3 -- device --> S4["S4 显示：serial、厂商、型号、Android、SDK、ABI"]

    S4 --> Q4{"问题：确认目标 / 换一台 / 退出"}
    Q4 -- 换一台 --> S2
    Q4 -- 退出 --> END0
    Q4 -- 确认 --> S5["S5 只读盘点：空间、HOME、已装包、目录版本"]
    S5 --> Q5{"问题：推荐配置 / 选择应用 / 本地 APK / 桌面清理 / 故障诊断 / 生成报告 / 退出"}
    Q5 -- 生成报告 --> S11
    Q5 -- 退出 --> END0
    Q5 -- 其余任务 --> S6["S6 结果：来源、SHA-256、兼容性、已装版本"]

    S6 --> D6{可执行？}
    D6 -- pending_rights --> Q6R{"问题：跳过 / 提交获授权本地 APK / 返回"}
    D6 -- pending_file --> Q6F{"问题：跳过 / 提交文件 / 返回"}
    Q6R -- 返回 --> Q5
    Q6F -- 返回 --> Q5
    Q6R -- 文件 --> S6
    Q6F -- 文件 --> S6
    Q6R -- 跳过 --> S7
    Q6F -- 跳过 --> S7
    D6 -- 可执行/已安装/不兼容 --> S7["S7 显示：编号计划、目标、来源、摘要、命令、影响、风险、恢复"]

    S7 --> Q8{"问题：批准全部 / 选择编号 / 修改 / 取消并报告 / 退出"}
    Q8 -- 修改 --> Q5
    Q8 -- 取消并报告 --> S11
    Q8 -- 退出 --> END0
    Q8 -- 批准 --> S9["S9 逐项执行并记录 stdout/stderr/exit/time"]
    S9 --> D9{出现新增高风险动作？}
    D9 -- 是 --> Q9{"问题：精确同意该动作 / 跳过 / 取消"}
    Q9 -- 同意 --> S9
    Q9 -- 跳过 --> S10
    Q9 -- 取消 --> S11
    D9 -- 否 --> S10["S10 显示：文件/安装/启动/运行信号证据"]

    S10 --> Q10{"问题：全部正常 / 无画面 / 无声音 / 遥控问题 / 启动崩溃 / 稍后验收 / 退出"}
    Q10 -- 全部正常 --> NEXT{还有批准项目？}
    Q10 -- 稍后验收 --> NEXT
    Q10 -- 故障 --> FIX{存在安全修复？}
    FIX -- 是 --> S7
    FIX -- 否 --> NEXT
    NEXT -- 是 --> S9
    NEXT -- 否 --> S11["S11 最终报告：变更、证据等级、未完成项、保留项、恢复命令、产物路径"]

    S11 --> Q11{"问题：完成并关闭调试 / 继续未完成项 / 保持现状退出"}
    Q11 -- 继续 --> S2
    Q11 -- 完成 --> END1["结果：提示用户关闭 ADB 调试"]
    Q11 -- 保持现状退出 --> END2["结果：保留当前状态和恢复记录"]
```

所有未明确、无效或过期的回答，都回到当前 `Q*`，不执行后续命令。完整协议见 [Interaction Contract](plugins/android-tv-apps-helper/skills/android-tv-apps-helper/references/interaction-contract.md) 和 [Workflow States](plugins/android-tv-apps-helper/skills/android-tv-apps-helper/references/workflow.md)。

## 用户看到的交互

宿主支持必填选择组件时，Agent 提交一个问题卡；否则显示同构文字菜单：

```text
问题 S4-Q1：这是要操作的电视吗？

1. 确认这台电视（推荐）——后续命令只发送到此设备
2. 换一台——返回设备发现
0. 安全退出——停止尚未执行的工作

请明确回复：1、2 或 0。
```

如果用户回复“好的”“随便”“你决定”或同时回复 `1,2`，状态不会前进，Agent 会解释一次并重复 `S4-Q1`。

## 安装插件

### ChatGPT 桌面版 / Codex App

```sh
git clone https://github.com/HXWfromDJTU/android-tv-apps-helper.git
cd android-tv-apps-helper
```

将仓库作为受信任项目打开并重启客户端。项目的 `.agents/plugins/marketplace.json` 会提供 `Android TV Tools` marketplace，安装其中的 `Android TV Apps Helper`。仓库内 `.codex/config.toml` 已为该项目启用插件。

### 支持 plugin marketplace 命令的 Codex CLI

```sh
codex plugin marketplace add HXWfromDJTU/android-tv-apps-helper --ref main
```

不同 Codex CLI 版本的插件命令可用性不同；若 `codex plugin --help` 不存在，请使用桌面端安装路径。

安装后可输入：

```text
使用 $android-tv-apps-helper 帮我配置这台 Android TV
```

## APK 下载策略

| 应用 | 状态 | 下载位置 |
|---|---|---|
| Clash Meta for Android 2.11.33 | 官方源 | 仅 [MetaCubeX 官方 Release](https://github.com/MetaCubeX/ClashMetaForAndroid/releases/tag/v2.11.33)，不镜像 |
| SmartTube 32.10 Stable | 可镜像 | 本项目 `v0.1.0` Release；字节与上游 Release 摘要一致 |
| 当贝市场、Emotn UI、奈飞工厂TV | 等待权利证明 | 不公开 APK 或下载 URL |
| 佳视通、乘风TV、魄狼TV | 等待文件和权利证明 | 不公开 APK 或下载 URL |

机器可读目录位于 [`catalog/apps.json`](plugins/android-tv-apps-helper/catalog/apps.json)，第三方声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。APK 二进制只放 GitHub Releases，不写入 Git 历史。

## Harness 命令

```sh
HELPER=plugins/android-tv-apps-helper/scripts/tv-helper

# 创建会话并锁定交互界面类型
$HELPER init-session outputs/demo/session.json --surface text_menu

# 校验目录；--eligible 只显示当前可下载项
$HELPER catalog --catalog plugins/android-tv-apps-helper/catalog/apps.json --eligible

# 枚举设备并读取目标身份
$HELPER adb-list
$HELPER adb-inspect --serial 192.168.1.20:5555 --state device

# 校验 APK，生成不可变计划，精确批准后才允许安装
$HELPER apk-inspect /absolute/app.apk --sha256 EXPECTED_SHA256
$HELPER plan-install outputs/demo/session.json --app-id app-id \
  --serial 192.168.1.20:5555 --apk /absolute/app.apk \
  --sha256 EXPECTED_SHA256 --out outputs/demo/plan.json
$HELPER approve-install outputs/demo/session.json \
  --plan outputs/demo/plan.json --confirmation confirm_install
$HELPER install-approved outputs/demo/session.json \
  --plan outputs/demo/plan.json --state device
```

`approve-install` 不接受泛化的 `yes` 或“继续”。安装前会再次计算 SHA-256，并核对批准的计划 ID、目标 serial 和设备状态。

## 开发与验证

仅依赖 Python 3.10+ 标准库：

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q plugins/android-tv-apps-helper/scripts
```

项目许可证为 [MIT](LICENSE)。第三方 APK 适用其各自许可证。
