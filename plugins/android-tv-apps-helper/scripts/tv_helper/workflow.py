from __future__ import annotations

from datetime import datetime
from typing import Any
from pathlib import Path
import json

from .guides import validate_wallpaper
from .evidence import validate_action_evidence
from .presentation import InteractionFrame, SummaryRow, render_markdown
from .questions import AnswerError, Option, Question, validate_answer
from .session import SessionStore
from .update import UpdateStateStore, record_update_decline, should_prompt_update


ADB_GUIDANCE = (
    "确认电脑和电视连接同一个可信 Wi-Fi。",
    "打开电视设置，进入‘系统/设备偏好设置 → 关于’。",
    "连续选择‘Build/版本’约 7 次，直到开发者选项开启。",
    "进入开发者选项，开启 ADB、网络调试或无线调试。",
    "在电视网络设置中查看电视 IP 地址。",
    "连接时只在电视上允许当前可信电脑的 RSA 授权。",
)
ADB_CLOSE_GUIDANCE = (
    "打开电视设置，进入‘系统/设备偏好设置 → 开发者选项’。",
    "关闭‘ADB 调试/网络调试/无线调试’。",
    "如果存在‘开发者选项’总开关，再将它关闭。",
)

WORKFLOW_STATES = {
    "UPDATE",
    "PRECHECK_WIFI",
    "ADB-SETUP",
    "PRECHECK_ADB",
    "DISCOVERY-NONE",
    "DISCOVERY-IP",
    "DISCOVERY-SCAN",
    "DISCOVERY-CONNECT",
    "TARGET-SELECT",
    "TARGET",
    "TASK",
    "APPS",
    "DOWNLOAD-CONFIRM",
    "DOWNLOAD-VERIFY",
    "INSTALL-PLAN",
    "VERIFY",
    "DANGBEI-SOURCE",
    "LAUNCHER-RISK",
    "HOME-CONFIRM",
    "DIAGNOSE",
    "WALLPAPER",
    "WALLPAPER-UPLOAD",
    "WALLPAPER-CONFIRM",
    "FINISH-SAFETY",
}
ACTION_STATES = {
    "UPDATE-ACTION",
    "ADB-VALIDATE-ACTION",
    "PASSIVE-DISCOVERY-ACTION",
    "CONNECT-ACTION",
    "SCAN-ACTION",
    "INSPECT-ACTION",
    "EMOTN-LAUNCH-ACTION",
    "DANGBEI-ACTION",
    "DANGBEI-PAGE-ACTION",
    "DIAGNOSE-ACTION",
    "DOWNLOAD-ACTION",
    "PREPARE-INSTALL-PLAN-ACTION",
    "INSTALL-ACTION",
    "HOME-ACTION",
    "WALLPAPER-ACTION",
    "FINISH-CHECK",
}
TERMINAL_STATES = {"END", "END-WARNING", "END-NO-ADB"}

EMOTN_PACKAGE = "com.oversea.aslauncher"


def _load_catalog() -> dict[str, Any]:
    root = Path(__file__).parents[2]
    for path in (root / "catalog" / "apps.json", root / "references" / "apps.json"):
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise ValueError("应用目录缺失，不能创建下载或安装动作。")


def _download_expectations(selected: tuple[str, ...]) -> list[dict[str, Any]]:
    by_id = {str(app["id"]): app for app in _load_catalog().get("apps", ())}
    expectations: list[dict[str, Any]] = []
    for app_id in selected:
        app = by_id.get(app_id)
        if not app or len(app.get("assets", ())) != 1:
            raise ValueError(f"{app_id} 没有唯一且已验证的下载文件。")
        asset = app["assets"][0]
        expectations.append(
            {
                "app_id": app_id,
                "url": asset["url"],
                "size": asset["size"],
                "sha256": asset["sha256"],
                "package": app.get("expected_package"),
                "version_name": app.get("expected_version_name"),
            }
        )
    return expectations


def _safe_exit(
    next_state: str = "END-NO-ADB",
    *,
    label: str = "安全退出",
    description: str = "停止尚未执行的操作",
) -> Option:
    return Option("safe_exit", label, next_state, description, shortcut="0")


def build_question(state: str, context: dict[str, Any]) -> Question:
    if state == "UPDATE":
        update_check = context.get("update_check") or {}
        update_exit = "FINISH-SAFETY" if (context.get("precheck") or {}).get("devices") else "END-NO-ADB"
        current = str(context.get("installed_version") or update_check.get("installed_version") or "当前版本")
        latest = str(context.get("latest_version") or update_check.get("latest_version") or "最新版本")
        return Question(
            question_id="UPDATE-Q1",
            state_id=state,
            kind="single_choice",
            prompt=f"检测到 Android TV Apps Helper {latest}，是否更新？",
            options=(
                Option("update", "更新后继续", "UPDATE-ACTION", "先下载并校验正确平台包，安装成功后再切换", True),
                Option("decline_24h", "暂不更新，24 小时内不再提醒", "PRECHECK_WIFI", "期间出现其他新版也不提示"),
                Option("release_notes", "查看完整更新说明", "UPDATE", "保持当前版本，不开始设备操作"),
                _safe_exit(update_exit),
            ),
            previous_result_summary=f"已安装 {current}；官方稳定版为 {latest}。",
            blocker_summary="更新不会在新包完成平台、Skill ID、版本和 SHA-256 校验前删除当前可用版本。",
            summary_rows=(
                {"status": "attention", "item": "Skill 更新", "result": f"{current} → {latest}"},
            ),
        )
    if state == "PRECHECK_WIFI":
        precheck = context.get("precheck", {})
        safety_exit = "FINISH-SAFETY" if precheck.get("devices") else "END-NO-ADB"
        adb_missing = any(
            row.get("item") == "ADB 工具" and row.get("result") == "未找到"
            for row in precheck.get("rows", ())
        )
        options = [
            Option("same_wifi", "已连接同一个 Wi-Fi", "PRECHECK_ADB", "继续核对电视调试权限", not adb_missing),
            Option("different_wifi", "目前不是同一个 Wi-Fi", "PRECHECK_WIFI", "先调整网络后再检查"),
            Option("unsure_wifi", "我不确定", "PRECHECK_WIFI", "查看电视和电脑的网络名称"),
        ]
        if adb_missing:
            options.insert(
                0,
                Option("configure_adb", "安装或指定 ADB 工具", "ADB-SETUP", "使用 Android 官方 Platform-Tools", True),
            )
        options.append(_safe_exit(safety_exit))
        return Question(
            question_id="PRECHECK-WIFI-Q1",
            state_id=state,
            kind="single_choice",
            prompt="请确认电脑和电视是否连接到同一个 Wi-Fi？",
            options=tuple(options),
            previous_result_summary="已完成自动、只读、被动预检查。",
            blocker_summary=(
                "本机未找到 ADB 工具；在完成安装或指定路径前不能发现电视。"
                if adb_missing else str(precheck.get("blocker", ""))
            ),
            remediation_guidance=(
                (
                    "从 Android Developers 官方 Platform-Tools 页面下载与你电脑系统匹配的版本。",
                    "解压后在下一题填写 adb 可执行文件的绝对路径；不会运行未校验的第三方安装器。",
                    "官方页面：https://developer.android.com/tools/releases/platform-tools",
                )
                if adb_missing else ADB_GUIDANCE[:1]
            ),
            summary_rows=tuple(precheck.get("rows", ())),
            display_name="确认同一 Wi-Fi",
        )
    if state == "ADB-SETUP":
        return Question(
            question_id="ADB-SETUP-Q1",
            state_id=state,
            kind="short_text",
            prompt="请填写 Android 官方 Platform-Tools 中 adb 可执行文件的绝对路径。",
            options=(
                Option("submit_adb", "提交并验证 ADB 路径", "ADB-VALIDATE-ACTION"),
                Option("show_official_guide", "再次查看 Android 官方安装页面", "ADB-SETUP"),
                Option("back", "返回预检查结果", "PRECHECK_WIFI"),
                _safe_exit(),
            ),
            input_prefix="ADB:",
            input_format="absolute_path",
            previous_result_summary="自动预检查没有找到可用的 ADB。",
            blocker_summary="只接受绝对路径；验证仅运行 adb version 和 adb devices -l。",
            remediation_guidance=(
                "官方下载：https://developer.android.com/tools/releases/platform-tools",
                "回答示例：ADB: /Users/me/Downloads/platform-tools/adb",
            ),
            summary_rows=(
                {"status": "failed", "item": "ADB 工具", "result": "未找到"},
                {"status": "pending", "item": "官方工具路径", "result": "等待填写"},
            ),
        )
    if state == "PRECHECK_ADB":
        return Question(
            question_id="PRECHECK-ADB-Q1",
            state_id=state,
            kind="single_choice",
            prompt="电视是否已开启 ADB、网络调试或无线调试？",
            options=(
                Option("adb_enabled", "已经开启", "PASSIVE-DISCOVERY-ACTION", "重新读取已授权设备", True),
                Option("show_guide", "还没开启，查看操作方法", "PRECHECK_ADB", "按下面步骤在电视上开启"),
                Option("unknown_adb", "我找不到这个设置", "PRECHECK_ADB", "继续查看品牌或通用指引"),
                _safe_exit(),
            ),
            previous_result_summary="已确认电脑与电视网络情况。",
            blocker_summary="未开启电视调试权限时，电脑无法通过 ADB 发现电视。",
            remediation_guidance=ADB_GUIDANCE,
            summary_rows=(
                {"status": "attention", "item": "电视调试权限", "result": "等待用户确认"},
            ),
        )
    if state == "DISCOVERY-NONE":
        attempts = int(context.get("attempts", (context.get("precheck") or {}).get("attempts", 1)))
        return Question(
            question_id="DISCOVERY-NONE-Q1",
            state_id=state,
            kind="single_choice",
            prompt="完成上述检查后，下一步怎么处理？",
            options=(
                Option("retry_passive", "重新执行被动检查", "PASSIVE-DISCOVERY-ACTION", "不扫描整个局域网", True),
                Option("submit_ip", "填写电视 IP 地址", "DISCOVERY-IP", "下一题会说明在哪里查看 IP"),
                Option("brand_guide", "查看电视品牌操作方法", "PRECHECK_ADB", "找不到设置时使用"),
                Option("approve_scan", "查看有限局域网扫描范围", "DISCOVERY-SCAN", "先显示范围，再单独批准"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary=f"第 {attempts} 次被动检查仍未发现已授权设备。",
            blocker_summary="当前没有可确认的电视；零结果不能证明电视未开启 ADB。",
            remediation_guidance=ADB_GUIDANCE,
            summary_rows=(
                {"status": "attention", "item": "设备发现", "result": f"第 {attempts} 次：0 个可确认设备"},
                {"status": "pending", "item": "主动扫描", "result": "未执行"},
            ),
            visual_aid="assets/adb-enable-generic.svg",
        )
    if state == "DISCOVERY-IP":
        return Question(
            question_id="DISCOVERY-IP-Q1",
            state_id=state,
            kind="short_text",
            prompt="请填写电视设置中显示的 IPv4 地址。",
            options=(
                Option("submit_ip", "提交电视 IP", "DISCOVERY-CONNECT"),
                Option("back", "返回设备发现", "DISCOVERY-NONE"),
                _safe_exit("FINISH-SAFETY"),
            ),
            input_prefix="IP:",
            input_format="ipv4",
            previous_result_summary="被动检查没有找到设备，现改用用户确认的单个地址。",
            blocker_summary="只填写电视设置页中的地址；不要填写路由器或其他设备地址。",
            remediation_guidance=("电视 IP 通常位于‘设置 → 网络 → 当前 Wi-Fi’。", "回答示例：IP: 192.168.1.20"),
            summary_rows=(
                {"status": "attention", "item": "电视 IP", "result": "等待填写"},
            ),
        )
    if state == "DISCOVERY-CONNECT":
        return Question(
            question_id="DISCOVERY-CONNECT-Q1",
            state_id=state,
            kind="explicit_consent",
            prompt="是否仅尝试连接刚才填写的电视地址？",
            options=(
                Option("connect_selected_ip", "连接这个地址", "CONNECT-ACTION", "只执行 adb connect 到该地址", True),
                Option("back", "返回修改 IP", "DISCOVERY-IP"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary="已记录一个用户确认的电视 IP。",
            blocker_summary="连接可能让电视弹出 RSA 授权框，但不会安装应用或修改设置。",
            summary_rows=(
                {"status": "pending", "item": "ADB 连接", "result": "等待批准"},
            ),
        )
    if state == "DISCOVERY-SCAN":
        approval = (context.get("precheck") or {}).get("scan_approval") or {}
        scope = tuple(approval.get("scope", ()))
        ports = tuple(approval.get("ports", ()))
        ready = bool(scope and ports)
        return Question(
            question_id="DISCOVERY-SCAN-Q1",
            state_id=state,
            kind="explicit_consent",
            prompt="是否按显示范围执行一次有限的电视 ADB 端口扫描？",
            options=(
                Option(
                    "approve_bounded_scan", "批准显示范围内的有限扫描", "SCAN-ACTION",
                    "只扫描列出的子网和端口", True, enabled=ready,
                    unavailable_reason="未读取到可信的私有 IPv4 子网，不能执行扫描。",
                ),
                Option("back", "返回被动发现", "DISCOVERY-NONE"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary="被动发现没有结果；尚未执行主动扫描。",
            blocker_summary="范围、端口和目的必须先在表格中列明；未知范围不能批准。",
            summary_rows=(
                {"status": "pending" if ready else "failed", "item": "扫描范围", "result": "、".join(scope) if scope else "无法确定"},
                {"status": "pending" if ready else "failed", "item": "扫描端口", "result": "、".join(map(str, ports)) if ports else "无法确定"},
            ),
        )
    if state == "TARGET-SELECT":
        devices = tuple((context.get("precheck") or {}).get("devices", ()))
        options = []
        rows = []
        for index, device in enumerate(devices, 1):
            model = next(
                (
                    str(item).split(":", 1)[1]
                    for item in device.get("details", ())
                    if str(item).startswith("model:")
                ),
                "型号待确认",
            )
            options.append(
                Option(f"candidate_{index}", f"候选设备 {index}：{model}", "TARGET")
            )
            rows.append(
                {"status": "attention", "item": f"候选设备 {index}", "result": model}
            )
        options.extend(
            (Option("back", "重新发现设备", "DISCOVERY-NONE"), _safe_exit("FINISH-SAFETY"))
        )
        return Question(
            question_id="TARGET-SELECT-Q1",
            state_id=state,
            kind="single_choice",
            prompt="请选择本次要操作的电视候选设备。",
            options=tuple(options),
            previous_result_summary=f"被动发现返回 {len(devices)} 个候选设备。",
            blocker_summary="必须先明确选择一台，后续命令才会绑定目标。",
            summary_rows=tuple(rows),
        )
    if state == "TARGET":
        return Question(
            question_id="TARGET-Q1",
            state_id=state,
            kind="single_choice",
            prompt="这是要操作的电视吗？",
            options=(
                Option("confirm_target", "确认这台电视", "INSPECT-ACTION", "先读取系统身份和应用清单，后续命令只发送到此设备", True),
                Option("choose_another", "换一台设备", "DISCOVERY-NONE"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary="已读取候选设备的只读身份信息。",
            blocker_summary="型号或系统无法确认时只显示‘可能是电视’，不会替你确定。",
            summary_rows=tuple(context.get("summary_rows", ({"status": "attention", "item": "目标候选", "result": "等待设备身份"},))),
        )
    if state == "TASK":
        installed = context.get("installed_apps") or {}
        emotn_installed = bool(installed.get("emotn-ui"))
        return Question(
            question_id="TASK-Q1",
            state_id=state,
            kind="single_choice",
            prompt="这次想处理哪一项？",
            options=(
                Option("recommended_apps", "查看并选择推荐应用", "APPS", "显示应用用途、版本和可用状态", True),
                Option("dangbei_source", "检查当贝市场官方来源", "DANGBEI-SOURCE", "自动重试官网来源，不需要用户找 APK"),
                Option(
                    "launcher_setup",
                    "设置电视默认桌面",
                    "EMOTN-LAUNCH-ACTION",
                    "先启动并验证 Emotn UI，再配置 Home 键和壁纸",
                    enabled=emotn_installed,
                    unavailable_reason="未验证 Emotn UI 已安装；请先完成应用安装流程。",
                ),
                Option("diagnose_app", "检查应用问题", "DIAGNOSE", "排查启动、画面、声音或遥控问题"),
                _safe_exit(
                    "FINISH-SAFETY",
                    label="结束本次任务，保留当前桌面和壁纸",
                    description="保存报告并进入安全收尾",
                ),
            ),
            previous_result_summary="已完成目标电视确认和只读盘点。",
            summary_rows=tuple(context.get("summary_rows", ())),
        )
    if state == "APPS":
        installed = context.get("installed_apps", {})
        app_defs = (
            ("clash-meta", "Clash Meta for Android", "2.11.33", "网络代理工具", True, "来自 MetaCubeX 官方 GitHub Release"),
            ("smarttube", "SmartTube", "32.10 Stable", "在线视频播放器", True, "来自本项目已核验 Release 资源"),
            ("dangbei-market", "当贝市场", "6.0.7", "电视应用市场", False, "官方地址已记录，包体身份待项目维护者验证；可返回任务菜单检查官方来源"),
            ("emotn-ui", "Emotn UI", "1.1.0.1", "电视桌面和壁纸", False, "当前没有可公开分发的已验证安装源；已安装设备仍可进入桌面设置"),
            ("jiashitong", "佳视通", "1.0.0", "观看电视直播内容", False, "安装文件和公开分发许可尚未核验"),
            ("chengfeng-tv", "乘风TV", "1.0.3", "观看电视直播内容", False, "安装文件和公开分发许可尚未核验"),
            ("polang-tv", "魄狼TV", "1.0.7", "观看电视直播内容", False, "安装文件和公开分发许可尚未核验"),
            ("nfgc-tv", "奈飞工厂TV", "9.0.1 test", "浏览和播放影视内容", False, "发布者身份和公开分发许可尚未核验"),
        )
        options = []
        rows = []
        for app_id, name, version, purpose, source_ready, reason in app_defs:
            current = installed.get(app_id)
            enabled = source_ready and current != version
            availability = "已是最新版本" if current == version else ("可以下载" if enabled else reason)
            options.append(
                Option(
                    app_id,
                    f"{name} {version}",
                    "DOWNLOAD-CONFIRM",
                    purpose,
                    enabled=enabled,
                    unavailable_reason=availability,
                )
            )
            rows.append(
                {
                    "status": "completed" if current == version else ("pending" if enabled else "attention"),
                    "item": name,
                    "result": availability,
                    "evidence": purpose,
                }
            )
        options.extend((Option("back", "返回任务选择", "TASK"), _safe_exit("FINISH-SAFETY")))
        return Question(
            question_id="APPS-Q1",
            state_id=state,
            kind="multi_choice",
            prompt="请选择要下载的应用。",
            options=tuple(options),
            previous_result_summary="已读取推荐应用、版本、用途和来源状态。",
            blocker_summary="灰色或标为不可用的项目不能加入下载清单。",
            remediation_guidance=("原生组件支持多选时直接勾选；文字模式回复示例：1、2。", "选择后会按应用名称和版本再次确认。"),
            summary_rows=tuple(rows),
        )
    if state == "DOWNLOAD-CONFIRM":
        selected = tuple(context.get("selected_apps", ()))
        labels = {
            "clash-meta": "Clash Meta for Android 2.11.33",
            "smarttube": "SmartTube 32.10 Stable",
        }
        names = tuple(labels.get(item, str(item)) for item in selected) or ("已选择的应用",)
        return Question(
            question_id="DOWNLOAD-CONFIRM-Q1",
            state_id=state,
            kind="explicit_consent",
            prompt="是否下载并校验这些应用：" + "、".join(names) + "？",
            options=(
                Option("confirm_download", "确认下载这些应用", "DOWNLOAD-ACTION", "只下载和校验，不安装", True),
                Option("back", "返回应用列表", "APPS"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary="已将编号解析为应用名称和版本。",
            blocker_summary="下载确认不等于安装批准。",
            summary_rows=tuple(
                {"status": "pending", "item": name, "result": "等待下载确认"}
                for name in names
            ),
        )
    if state == "DOWNLOAD-VERIFY":
        return Question(
            question_id="DOWNLOAD-VERIFY-Q1",
            state_id=state,
            kind="single_choice",
            prompt="下载与文件校验完成后，下一步怎么处理？",
            options=(
                Option("review_install_plan", "生成并查看安装计划", "PREPARE-INSTALL-PLAN-ACTION", "读取已验证文件并绑定当前电视，尚不安装", True),
                Option("back", "返回应用列表", "APPS"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary="下载结果必须按应用显示来源、大小、SHA-256 和包体身份。",
            summary_rows=tuple(context.get("download_rows", ({"status": "pending", "item": "下载校验", "result": "等待执行"},))),
        )
    if state == "INSTALL-PLAN":
        plan = context.get("approved_plan") or {}
        ready = plan.get("status") in {"planned", "approved"}
        catalog_names = {
            str(app.get("id")): f"{app.get('name')} {app.get('version')}"
            for app in _load_catalog().get("apps", ())
        }
        if plan.get("action") == "install_bundle":
            plan_names = "、".join(catalog_names.get(str(item.get("app_id")), "已验证应用") for item in plan.get("installations", ()))
            plan_digest = "计划与 APK 摘要已绑定"
        else:
            plan_names = catalog_names.get(str(plan.get("app_id")), "已验证应用")
            plan_digest = "计划与 APK 摘要已绑定" if ready else ""
        plan_rows = (
            {
                "status": "pending" if ready else "failed",
                "item": "方案 01：安装应用",
                "result": (
                    f"{plan_names} → {plan.get('serial')}"
                    if ready else "尚未从已验证下载生成计划"
                ),
                "evidence": plan_digest,
            },
        )
        return Question(
            question_id="INSTALL-PLAN-Q1",
            state_id=state,
            kind="explicit_consent",
            prompt="是否批准显示的安装计划？",
            options=(
                Option(
                    "approve_install", "批准安装计划", "INSTALL-ACTION",
                    "只执行表格内绑定设备和摘要的安装", True,
                    enabled=ready,
                    unavailable_reason="请先让 Agent 从已验证下载文件生成安装计划。",
                ),
                Option("back", "返回应用列表", "APPS"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary="已生成友好名称和不可变内部计划。",
            blocker_summary="设备、摘要、命令或风险变化会使批准失效。",
            summary_rows=tuple(context.get("plan_rows", plan_rows)),
        )
    if state == "VERIFY":
        return Question(
            question_id="VERIFY-Q1",
            state_id=state,
            kind="single_choice",
            prompt="请根据电视现场情况选择验收结果。",
            options=(
                Option("all_normal", "画面、声音和遥控都正常", "TASK", "记录现场验收", True),
                Option("picture_problem", "没有画面或画面异常", "DIAGNOSE"),
                Option("sound_problem", "没有声音", "DIAGNOSE"),
                Option("remote_problem", "遥控器无法正常操作", "DIAGNOSE"),
                Option("defer", "稍后再验收", "TASK", "保留为待确认"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary="命令结果已记录，但不代替电视现场验收。",
            summary_rows=tuple(context.get("evidence_rows", ({"status": "attention", "item": "现场验收", "result": "等待用户确认"},))),
        )
    if state == "DANGBEI-SOURCE":
        error = str(context.get("source_error", "官方来源当前不可达"))
        return Question(
            question_id="DANGBEI-SOURCE-Q1",
            state_id=state,
            kind="single_choice",
            prompt="当贝市场的官方来源当前不可用，怎么继续？",
            options=(
                Option("retry_official", "重试当贝官方来源", "DANGBEI-ACTION", "仅访问固定官网和允许域名", True),
                Option("open_publisher", "查看当贝官方页面", "DANGBEI-PAGE-ACTION", "仅查看来源，不要求你自行寻找 APK"),
                Option("skip_app", "暂时跳过当贝市场", "APPS", "继续处理其他应用"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary="已定位当贝官网稳定版，但下载或包体验证未完成。",
            blocker_summary=error,
            remediation_guidance=("不会改用论坛、网盘或未知 GitHub 镜像。",),
            summary_rows=(
                {"status": "failed", "item": "当贝市场", "result": error},
                {"status": "completed", "item": "来源保护", "result": "未使用未知镜像"},
            ),
        )
    if state == "LAUNCHER-RISK":
        identity = context.get("device_identity") or {}
        name = str(
            context.get("device_name")
            or identity.get("display_name")
            or identity.get("model")
            or "当前电视（型号待核实）"
        )
        stored_risks = context.get("compatibility_matches", ())
        risk_rows = tuple(
            {
                "status": "attention",
                "item": row.get("label", row.get("item", "兼容性")),
                "result": row.get("message", row.get("result", "")),
                "evidence": row.get("evidence", ""),
            }
            for row in stored_risks
        )
        return Question(
            question_id="LAUNCHER-RISK-Q1",
            state_id=state,
            kind="single_choice",
            prompt="了解风险后，这次要尝试哪项桌面设置？",
            options=(
                Option("wallpaper_only", "只设置壁纸", "WALLPAPER", "不修改 Home 键", True),
                Option("home_only", "只尝试修改 Home 键默认桌面", "HOME-CONFIRM", "需要后续独立执行批准"),
                Option("both", "同时选择 Home 键和壁纸", "HOME-CONFIRM", "先单独批准 Home，再选择壁纸"),
                Option("back", "返回任务选择", "TASK"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary=f"已识别目标：{name}。",
            blocker_summary="没有匹配证据时只能标记为未知；当前系统可能限制 Home 键或稍后恢复壁纸。",
            remediation_guidance=("原厂桌面不会被卸载、禁用或清除数据。", "风险确认不是执行批准。"),
            summary_rows=(
                {"status": "completed", "item": "目标电视", "result": name},
                *(risk_rows or tuple(
                    context.get(
                        "compatibility_rows",
                        (
                            {"status": "attention", "item": "修改壁纸", "result": "兼容性未知，可能失败或被重置"},
                            {"status": "attention", "item": "修改 Home 键", "result": "兼容性未知，可能失败"},
                        ),
                    )
                )),
            ),
        )
    if state == "HOME-CONFIRM":
        identity = context.get("device_identity") or {}
        name = str(identity.get("display_name") or identity.get("model") or "当前电视（型号待核实）")
        risks = tuple(context.get("compatibility_matches", ()))
        return Question(
            question_id="HOME-CONFIRM-Q1",
            state_id=state,
            kind="explicit_consent",
            prompt="是否批准本方案尝试把 Home 键指向 Emotn UI？",
            options=(
                Option("approve_home", "批准这一次 Home 键修改", "HOME-ACTION", "保留原厂桌面和恢复路径", True),
                Option("back", "返回风险选择", "LAUNCHER-RISK"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary="已阅读当前型号的 Home 键兼容性风险；尚未执行修改。",
            blocker_summary="风险确认不等于执行批准；失败后不会禁用或卸载原厂桌面。",
            summary_rows=(
                {"status": "completed", "item": "目标电视", "result": name},
                *(tuple(
                    {
                        "status": "attention",
                        "item": row.get("label", "修改 Home 键"),
                        "result": row.get("message", "大概率无法替换成功"),
                        "evidence": row.get("evidence", ""),
                    }
                    for row in risks if row.get("action") == "home_key"
                ) or ({"status": "attention", "item": "修改 Home 键", "result": "当前型号兼容性未知，大概率无法替换成功"},)),
                {"status": "pending", "item": "Home 键修改", "result": "等待独立执行批准"},
            ),
        )
    if state == "DIAGNOSE":
        return Question(
            question_id="DIAGNOSE-Q1",
            state_id=state,
            kind="single_choice",
            prompt="现在主要遇到哪一种问题？",
            options=(
                Option("launch", "应用无法启动或闪退", "DIAGNOSE-ACTION", "收集限定的启动日志", True),
                Option("picture", "没有画面或画面异常", "DIAGNOSE-ACTION", "检查前台和解码信号"),
                Option("sound", "没有声音", "DIAGNOSE-ACTION", "检查音频信号"),
                Option("remote", "遥控器无法操作", "DIAGNOSE-ACTION", "检查焦点和按键响应"),
                Option("back", "返回任务选择", "TASK"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary="已保留当前电视和应用状态，尚未执行修复。",
            summary_rows=(
                {"status": "attention", "item": "问题类型", "result": "等待选择"},
            ),
        )
    if state == "WALLPAPER":
        identity = context.get("device_identity") or {}
        device_name = str(context.get("device_name") or identity.get("display_name") or identity.get("model") or "当前电视（型号待核实）")
        risks = tuple(context.get("compatibility_matches", ()))
        wallpaper_risks = tuple(
            {"status": "attention", "item": row.get("label", "修改壁纸"), "result": row.get("message", "大概率无法替换成功"), "evidence": row.get("evidence", "")}
            for row in risks if row.get("action") == "wallpaper"
        )
        return Question(
            question_id="WALLPAPER-Q1",
            state_id=state,
            kind="single_choice",
            prompt="安装或启动 Emotn UI 后，壁纸怎么设置？",
            options=(
                Option("upload_wallpaper", "上传一张自定义图片", "WALLPAPER-UPLOAD", "支持 PNG、JPEG、WebP，最大 20 MB", True),
                Option("default_wallpaper", "使用 Emotn UI 默认壁纸", "WALLPAPER-CONFIRM", "不会读取本地图片"),
                Option("back", "返回桌面设置", "LAUNCHER-RISK"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary=f"目标设备：{device_name}。",
            blocker_summary="自定义壁纸可能在几天后、重启、系统升级或桌面升级后被电视系统重置。",
            remediation_guidance=("上传失败不会自动改用默认壁纸。", "应用壁纸前还会再次确认。"),
            summary_rows=(
                {"status": "completed", "item": "目标电视", "result": device_name},
                *(wallpaper_risks or ({"status": "attention", "item": "修改壁纸", "result": "当前型号兼容性未知，可能失败"},)),
                {"status": "attention", "item": "壁纸持久性", "result": "厂商系统可能重置"},
            ),
        )
    if state == "WALLPAPER-UPLOAD":
        identity = context.get("device_identity") or {}
        device_name = str(identity.get("display_name") or identity.get("model") or "当前电视（型号待核实）")
        risks = tuple(context.get("compatibility_matches", ()))
        wallpaper_risks = tuple(
            {"status": "attention", "item": row.get("label", "修改壁纸"), "result": row.get("message", "大概率无法替换成功"), "evidence": row.get("evidence", "")}
            for row in risks if row.get("action") == "wallpaper"
        )
        return Question(
            question_id="WALLPAPER-UPLOAD-Q1",
            state_id=state,
            kind="short_text",
            prompt="请上传一张图片，或填写它在本机的绝对路径。",
            options=(
                Option("submit_wallpaper", "提交图片", "WALLPAPER-CONFIRM"),
                Option("use_default", "改用 Emotn UI 默认壁纸", "WALLPAPER-CONFIRM"),
                Option("back", "返回壁纸选择", "WALLPAPER"),
                _safe_exit("FINISH-SAFETY"),
            ),
            input_prefix="图片:",
            input_format="absolute_path",
            previous_result_summary="已选择自定义壁纸；尚未读取或传输图片。",
            blocker_summary="缺失、格式错误、超过 20 MB 或传输失败都会停留在本题；即使成功，厂商系统也可能在几天后、重启或升级后重置壁纸。",
            remediation_guidance=("支持 PNG、JPEG、WebP，最大 20 MB；推荐横屏 16:9。", "回答示例：图片: /Users/me/Pictures/tv.jpg"),
            summary_rows=(
                {"status": "completed", "item": "目标电视", "result": device_name},
                *(wallpaper_risks or ({"status": "attention", "item": "修改壁纸", "result": "当前型号兼容性未知，可能失败"},)),
                {"status": "pending", "item": "壁纸图片", "result": "等待上传"},
                {"status": "attention", "item": "壁纸持久性", "result": "几天后、重启或升级后可能被重置"},
            ),
        )
    if state == "WALLPAPER-CONFIRM":
        asset = context.get("wallpaper_asset") or {"media_type": "默认壁纸", "size": 0}
        identity = context.get("device_identity") or {}
        device_name = str(identity.get("display_name") or identity.get("model") or "当前电视（型号待核实）")
        is_default = asset.get("kind") == "default" or asset.get("media_type") == "默认壁纸"
        target_label = "Emotn UI 默认壁纸" if is_default else "已校验的自定义图片"
        risks = tuple(context.get("compatibility_matches", ()))
        wallpaper_risks = tuple(
            {"status": "attention", "item": row.get("label", "修改壁纸"), "result": row.get("message", "大概率无法替换成功"), "evidence": row.get("evidence", "")}
            for row in risks if row.get("action") == "wallpaper"
        )
        return Question(
            question_id="WALLPAPER-CONFIRM-Q1",
            state_id=state,
            kind="explicit_consent",
            prompt=f"是否把{target_label}应用到 Emotn UI？",
            options=(
                Option("apply_wallpaper", f"确认应用{target_label}", "WALLPAPER-ACTION", "只修改 Emotn UI 壁纸", True),
                Option("choose_again", "重新选择壁纸", "WALLPAPER"),
                _safe_exit("FINISH-SAFETY"),
            ),
            previous_result_summary="图片已完成本地格式和大小校验。",
            blocker_summary="电视系统仍可能在几天后、重启或升级后重置壁纸。",
            summary_rows=(
                {"status": "completed", "item": "目标电视", "result": device_name},
                *(wallpaper_risks or ({"status": "attention", "item": "修改壁纸", "result": "当前型号兼容性未知，可能失败"},)),
                {"status": "completed", "item": "壁纸选择", "result": target_label, "evidence": str(asset.get("sha256", "默认资源"))[:12]},
                {"status": "attention", "item": "持久性", "result": "可能被厂商系统重置"},
            ),
        )
    if state == "FINISH-SAFETY":
        guide = context.get("device_guide_match") or {}
        identity = context.get("device_identity") or {}
        name = str(
            context.get("device_name")
            or guide.get("display_name")
            or identity.get("display_name")
            or identity.get("model")
            or "当前电视（型号未确认）"
        )
        steps = tuple(
            context.get("guide_steps")
            or guide.get("disable_steps")
            or ADB_CLOSE_GUIDANCE
        )
        return Question(
            question_id="FINISH-SAFETY-Q1",
            state_id=state,
            kind="single_choice",
            prompt="请确认电视上的 ADB 调试和开发者模式是否已经关闭？",
            options=(
                Option("both_closed", "两项都已关闭", "FINISH-CHECK", "执行一次只读冲突复核后记录", True),
                Option("show_model_guide", "找不到设置，查看本型号详细指引", "FINISH-SAFETY", "继续停留在本题"),
                Option("keep_enabled", "暂时保持开启并结束", "END-WARNING", "最终报告保留安全警告", shortcut="0"),
            ),
            previous_result_summary=f"已保存本次操作记录；目标设备为 {name}。",
            blocker_summary="ADB 保持开启会允许同一网络中的已授权电脑继续访问电视。",
            remediation_guidance=steps,
            summary_rows=(
                {"status": "completed", "item": "目标电视", "result": name},
                {"status": "attention", "item": "ADB 调试", "result": "等待用户关闭并确认"},
                {"status": "attention", "item": "开发者模式", "result": "等待用户关闭并确认"},
            ),
        )
    raise ValueError(f"Unsupported workflow state: {state}")


def render_question(question: Question) -> str:
    rows = tuple(
        SummaryRow(
            str(row.get("status", "pending")),
            str(row.get("item", "事项")),
            str(row.get("result", "")),
            str(row.get("evidence", "")),
        )
        for row in question.summary_rows
    )
    if question.previous_result_summary:
        rows = (
            SummaryRow("completed", "上一轮/当前进度", question.previous_result_summary),
            *rows,
        )
    if not rows:
        rows = (SummaryRow("pending", "当前进度", "等待处理"),)
    numbered = [
        option.shortcut or str(index)
        for index, option in enumerate(question.options, 1)
        if option.enabled
    ]
    if question.kind == "multi_choice":
        accepted = "请用原生多选，或回复编号并用分隔符连接，例如：1、2；返回/退出须单独选择。"
    elif question.kind == "short_text":
        accepted = f"请按“{question.input_prefix}…”格式回答，或明确回复：" + "、".join(numbered[1:]) + "。"
    else:
        accepted = "请明确回复：" + "、".join(numbered) + "。"
    frame_options = []
    start = 2 if question.kind == "short_text" else 1
    visible_options = question.options[1:] if question.kind == "short_text" else question.options
    for original_index, option in enumerate(visible_options, start=start):
        label = option.label
        description = option.description
        if option.recommended:
            label += "（推荐）"
        if not option.enabled:
            label += "（不可选）"
            description = option.unavailable_reason or description
        frame_options.append((option.value, label, description, option.shortcut or str(original_index)))
    frame = InteractionFrame(
        rows=rows,
        blocker=question.blocker_summary,
        guidance=question.remediation_guidance,
        question_id=question.question_id,
        question=question.prompt,
        options=tuple(frame_options),
        accepted_answer=accepted,
    )
    return render_markdown(frame)


class WorkflowEngine:
    def __init__(self, store: SessionStore):
        self.store = store

    def start(self, precheck: dict[str, Any]) -> Question:
        self.store.update_fields(precheck=precheck, current_state="PRECHECK_WIFI")
        question = build_question("PRECHECK_WIFI", {"precheck": precheck})
        self.store.set_question(question)
        return question

    def enter(
        self,
        precheck: dict[str, Any],
        *,
        installed_version: str,
        latest_release: dict[str, Any] | None,
        update_state_store: UpdateStateStore,
        now: datetime | None = None,
    ) -> Question:
        data = self.store.read()
        if data.get("pending_question") or data.get("pending_action"):
            raise AnswerError("当前会话仍有待回答问题或待回传操作，不能重新进入工作流。")
        update_state = update_state_store.read()
        update_check: dict[str, Any] = {
            "installed_version": installed_version,
            "checked": True,
            "state_error": update_state.get("state_error"),
            "checked_at": now.isoformat() if now else None,
        }
        latest_version = None
        if latest_release:
            latest_version = str(latest_release.get("version", ""))
            update_check.update(
                {
                    "latest_version": latest_version,
                    "release": latest_release.get("release", {}),
                }
            )
        self.store.update_fields(
            precheck=precheck,
            update_check=update_check,
            update_state_path=str(update_state_store.path),
        )
        if latest_version and should_prompt_update(
            installed_version, latest_version, update_state, now=now
        ):
            self.store.update_fields(current_state="UPDATE")
            question = build_question(
                "UPDATE",
                {
                    **self.store.read(),
                    "installed_version": installed_version,
                    "latest_version": latest_version,
                },
            )
            self.store.set_question(question)
            return question
        return self.start(precheck)

    def submit(self, raw: str | None, *, question_id: str) -> dict[str, Any]:
        data = self.store.read()
        pending = data.get("pending_question")
        if not pending:
            return {"accepted": False, "error": "当前没有待回答的问题。", "question": None}
        current = Question.from_dict(pending)
        try:
            proposed = validate_answer(current, raw, submitted_question_id=question_id)
        except AnswerError as error:
            try:
                self.store.answer(raw, submitted_question_id=question_id)
            except AnswerError:
                pass
            question = Question.from_dict(self.store.read()["pending_question"])
            invalid = Question(
                **{
                    **question.__dict__,
                    "blocker_summary": f"回答无效：{error}"
                    + (f" 当前阻塞仍是：{question.blocker_summary}" if question.blocker_summary else ""),
                    "summary_rows": (
                        {"status": "failed", "item": "本次回答", "result": str(error)},
                        *question.summary_rows,
                    ),
                }
            )
            self.store.replace_pending_context(invalid)
            return {"accepted": False, "error": str(error), "question": invalid}

        if current.state_id == "UPDATE" and proposed.value == "decline_24h":
            state_path = data.get("update_state_path")
            latest = str(data.get("update_check", {}).get("latest_version", "unknown"))
            if not state_path:
                raise AnswerError("更新提醒状态路径缺失，不能可靠记录 24 小时免打扰。")
            state_store = UpdateStateStore(Path(state_path))
            checked_at = data.get("update_check", {}).get("checked_at")
            decline_now = datetime.fromisoformat(checked_at) if checked_at else None
            state_store.write(
                record_update_decline(state_store.read(), latest, now=decline_now)
            )

        derived: dict[str, Any] = {}
        next_context = dict(data)
        if current.state_id == "DISCOVERY-IP" and isinstance(proposed.value, str):
            if proposed.value not in {"back", "safe_exit"}:
                derived["candidate_ip"] = proposed.value
                next_context["candidate_ip"] = proposed.value
        if current.state_id == "ADB-SETUP" and isinstance(proposed.value, str):
            if proposed.value not in {"show_official_guide", "back", "safe_exit"}:
                derived["adb_path"] = proposed.value
                next_context["adb_path"] = proposed.value
        if current.state_id == "TARGET-SELECT" and isinstance(proposed.value, str):
            if proposed.value.startswith("candidate_"):
                index = int(proposed.value.rsplit("_", 1)[1]) - 1
                devices = tuple((data.get("precheck") or {}).get("devices", ()))
                if index < 0 or index >= len(devices):
                    raise AnswerError("候选设备编号已变化，请重新发现设备。")
                serial = devices[index].get("serial")
                derived["target_serial"] = serial
                next_context["target_serial"] = serial
        if current.state_id == "APPS" and isinstance(proposed.value, tuple):
            app_values = tuple(value for value in proposed.value if value not in {"back", "safe_exit"})
            derived["selected_apps"] = list(app_values)
            next_context["selected_apps"] = list(app_values)
        if current.state_id == "LAUNCHER-RISK":
            selected_actions = {
                "wallpaper_only": ["wallpaper"],
                "home_only": ["home_key"],
                "both": ["home_key", "wallpaper"],
            }.get(str(proposed.value))
            if selected_actions:
                derived["selected_launcher_actions"] = selected_actions
                next_context["selected_launcher_actions"] = selected_actions
        if current.state_id == "WALLPAPER-UPLOAD" and isinstance(proposed.value, str):
            if proposed.value == "use_default":
                asset = {"kind": "default", "media_type": "默认壁纸", "size": 0}
                derived["wallpaper_asset"] = asset
                next_context["wallpaper_asset"] = asset
            elif proposed.value not in {"back", "safe_exit"}:
                asset = validate_wallpaper(Path(proposed.value))
                if not asset["valid"]:
                    updated = Question(
                        **{
                            **current.__dict__,
                            "blocker_summary": str(asset["reason"]),
                            "summary_rows": (
                                {"status": "failed", "item": "壁纸图片", "result": str(asset["reason"])},
                            ),
                        }
                    )
                    self.store.replace_pending_context(updated)
                    return {"accepted": False, "error": asset["reason"], "question": updated}
                derived["wallpaper_asset"] = asset
                next_context["wallpaper_asset"] = asset
        if current.state_id == "WALLPAPER" and proposed.value == "default_wallpaper":
            asset = {"kind": "default", "media_type": "默认壁纸", "size": 0}
            derived["wallpaper_asset"] = asset
            next_context["wallpaper_asset"] = asset

        terminal = proposed.next_state in TERMINAL_STATES
        action_required = proposed.next_state in ACTION_STATES
        action_bindings: dict[str, Any] = {}
        try:
            if proposed.next_state == "DOWNLOAD-ACTION":
                action_bindings["download_expectations"] = _download_expectations(
                    tuple(next_context.get("selected_apps", ()))
                )
            if proposed.next_state == "SCAN-ACTION":
                approval = (next_context.get("precheck") or {}).get("scan_approval")
                if not approval:
                    raise ValueError("未生成可核对的有限扫描范围。")
                action_bindings["scan_approval"] = approval
            if proposed.next_state == "INSTALL-ACTION":
                plan = next_context.get("approved_plan")
                if not isinstance(plan, dict) or plan.get("status") not in {"planned", "approved"}:
                    raise ValueError("尚未从已验证下载文件生成不可变安装计划。")
                if str(plan.get("serial")) != str(next_context.get("target_serial")):
                    raise ValueError("安装计划绑定的电视与当前目标不一致。")
                files = tuple(next_context.get("verified_downloads", ()))
                expected = {(item.get("app_id"), item.get("sha256")) for item in files}
                if plan.get("action") == "install_bundle":
                    actual = {(item.get("app_id"), (item.get("apk") or {}).get("sha256")) for item in plan.get("installations", ())}
                else:
                    actual = {(plan.get("app_id"), (plan.get("apk") or {}).get("sha256"))}
                if not expected or actual != expected:
                    raise ValueError("安装计划未绑定刚完成验证的 APK 摘要。")
                plan = {**plan, "status": "approved"}
                self.store.set_approved_plan(plan)
                next_context["approved_plan"] = plan
                action_bindings["approved_plan"] = plan
            if proposed.next_state in {"HOME-ACTION", "WALLPAPER-ACTION"}:
                runtime = next_context.get("emotn_runtime") or {}
                if runtime.get("verified") is not True or runtime.get("package") != EMOTN_PACKAGE:
                    raise ValueError("尚未验证 Emotn UI 位于前台，不能修改 Home 键或壁纸。")
        except ValueError as error:
            updated = Question(
                **{
                    **current.__dict__,
                    "blocker_summary": str(error),
                    "summary_rows": (
                        {"status": "failed", "item": "执行前检查", "result": str(error)},
                        *current.summary_rows,
                    ),
                }
            )
            self.store.replace_pending_context(updated)
            return {"accepted": False, "error": str(error), "question": updated}
        target_required = {
            "CONNECT-ACTION",
            "INSPECT-ACTION",
            "EMOTN-LAUNCH-ACTION",
            "PREPARE-INSTALL-PLAN-ACTION",
            "INSTALL-ACTION",
            "DIAGNOSE-ACTION",
            "HOME-ACTION",
            "WALLPAPER-ACTION",
            "FINISH-CHECK",
        }
        if action_required and proposed.next_state in target_required:
            target = next_context.get("target_serial")
            if proposed.next_state == "CONNECT-ACTION":
                target = next_context.get("candidate_ip")
            if not target:
                updated = Question(
                    **{
                        **current.__dict__,
                        "blocker_summary": "尚未锁定目标电视，不能开始这项操作。请返回设备发现并确认一台电视。",
                        "summary_rows": (
                            {"status": "failed", "item": "目标电视", "result": "未锁定"},
                        ),
                    }
                )
                self.store.replace_pending_context(updated)
                return {"accepted": False, "error": updated.blocker_summary, "question": updated}
        next_question = (
            None
            if terminal or action_required
            else build_question(proposed.next_state, next_context)
        )

        answer = self.store.answer(raw, submitted_question_id=question_id)
        if derived:
            self.store.update_fields(**derived)
        if terminal:
            if current.state_id == "FINISH-SAFETY":
                self.store.update_fields(
                    finish_safety={
                        **data.get("finish_safety", {}),
                        "user_confirmation": answer.value,
                        "completed": answer.value == "both_closed",
                    }
                )
            return {"accepted": True, "answer": answer, "question": None}
        if action_required:
            action = {
                "action_id": proposed.next_state,
                "status": "pending",
                "source_question_id": current.question_id,
                "selected_apps": next_context.get("selected_apps", []),
                "selected_actions": next_context.get("selected_launcher_actions", []),
                "wallpaper_asset": next_context.get("wallpaper_asset"),
                "update_check": next_context.get("update_check", {}),
                "precheck": next_context.get("precheck", {}),
                "candidate_ip": next_context.get("candidate_ip"),
                "target_serial": next_context.get("target_serial"),
                "requested_operation": proposed.value,
                "emotn_runtime": next_context.get("emotn_runtime", {}),
                "installed_apps": next_context.get("installed_apps", {}),
                "host_platform": next_context.get("host_platform"),
                "adb_path": next_context.get("adb_path"),
                "verified_downloads": next_context.get("verified_downloads", []),
                "approved_plan": next_context.get("approved_plan"),
                "expected_home_package": EMOTN_PACKAGE,
                "dangbei_expectation": next(
                    (app for app in _load_catalog().get("apps", ()) if app.get("id") == "dangbei-market"),
                    {},
                ) if proposed.next_state == "DANGBEI-ACTION" else {},
                **action_bindings,
            }
            self.store.set_pending_action(action)
            return {
                "accepted": True,
                "answer": answer,
                "question": None,
                "action_required": action,
            }
        assert next_question is not None
        self.store.set_question(next_question)
        return {"accepted": True, "answer": answer, "question": next_question}

    def record_action(
        self,
        action_id: str,
        *,
        status: str,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        data = self.store.read()
        pending = data.get("pending_action")
        try:
            validate_action_evidence(
                action_id, status=status, evidence=evidence, pending=pending
            )
        except ValueError as error:
            raise AnswerError(str(error)) from error
        record = self.store.complete_pending_action(
            action_id, status=status, evidence=evidence
        )
        context = {**self.store.read()}
        row_status = status
        result = str(evidence.get("result", status))
        if action_id == "FINISH-CHECK":
            reachable = bool(evidence.get("adb_still_reachable"))
            safety = {
                **context.get("finish_safety", {}),
                "user_confirmation": "both_closed",
                "adb_still_reachable": reachable,
                "completed": not reachable and status != "failed",
            }
            self.store.update_fields(finish_safety=safety)
            if reachable or status == "failed":
                question = build_question("FINISH-SAFETY", {**context, "finish_safety": safety})
                question = Question(
                    **{
                        **question.__dict__,
                        "blocker_summary": "你选择了两项都已关闭，但只读复核显示 ADB 仍可连接。请再次检查电视开关。",
                        "summary_rows": (
                            {"status": "failed", "item": "ADB 关闭复核", "result": "ADB 仍可连接"},
                            {"status": "attention", "item": "开发者模式", "result": "等待再次确认"},
                        ),
                    }
                )
                self.store.set_question(question)
                return {"accepted": False, "record": record, "question": question}
            self.store.update_fields(current_state="END")
            return {"accepted": True, "record": record, "question": None}

        if status != "completed":
            retry_state = {
                "UPDATE-ACTION": "UPDATE",
                "ADB-VALIDATE-ACTION": "ADB-SETUP",
                "PASSIVE-DISCOVERY-ACTION": "DISCOVERY-NONE",
                "CONNECT-ACTION": "DISCOVERY-CONNECT",
                "SCAN-ACTION": "DISCOVERY-SCAN",
                "INSPECT-ACTION": "TARGET",
                "EMOTN-LAUNCH-ACTION": "TASK",
                "DANGBEI-ACTION": "DANGBEI-SOURCE",
                "DANGBEI-PAGE-ACTION": "DANGBEI-SOURCE",
                "DIAGNOSE-ACTION": "DIAGNOSE",
                "DOWNLOAD-ACTION": "DOWNLOAD-CONFIRM",
                "PREPARE-INSTALL-PLAN-ACTION": "DOWNLOAD-VERIFY",
                "INSTALL-ACTION": "INSTALL-PLAN",
                "HOME-ACTION": "HOME-CONFIRM",
                "WALLPAPER-ACTION": "WALLPAPER-CONFIRM",
            }.get(action_id)
            if retry_state is None:
                raise AnswerError(f"不支持的操作结果：{action_id}")
            if retry_state == "UPDATE":
                update_check = context.get("update_check", {})
                context["installed_version"] = update_check.get("installed_version")
                context["latest_version"] = update_check.get("latest_version")
            question = build_question(retry_state, context)
            question = Question(
                **{
                    **question.__dict__,
                    "blocker_summary": f"上一次执行未完成：{result}",
                    "summary_rows": (
                        {"status": "failed", "item": "上一次执行", "result": result},
                        *question.summary_rows,
                    ),
                }
            )
            self.store.set_question(question)
            return {"accepted": False, "record": record, "question": question}

        if action_id == "UPDATE-ACTION":
            next_state = "PRECHECK_WIFI"
            context["precheck"] = context.get("precheck", {})
        elif action_id == "ADB-VALIDATE-ACTION":
            precheck = evidence.get("precheck") or context.get("precheck", {})
            self.store.update_fields(precheck=precheck)
            context["precheck"] = precheck
            next_state = "PRECHECK_WIFI"
        elif action_id in {"PASSIVE-DISCOVERY-ACTION", "SCAN-ACTION"}:
            discovered = evidence.get("precheck") or {
                **context.get("precheck", {}),
                "devices": evidence.get("devices", ()),
                "rows": evidence.get("rows", context.get("precheck", {}).get("rows", ())),
            }
            discovered["attempts"] = int(discovered.get("attempts", 0)) + 1
            self.store.update_fields(precheck=discovered)
            context["precheck"] = discovered
            devices = tuple(discovered.get("devices", ()))
            if len(devices) == 1:
                serial = devices[0].get("serial")
                self.store.update_fields(target_serial=serial)
                context["target_serial"] = serial
                next_state = "TARGET"
            elif len(devices) > 1:
                next_state = "TARGET-SELECT"
            else:
                next_state = "DISCOVERY-NONE"
        elif action_id == "CONNECT-ACTION":
            serial = evidence.get("target_serial") or (pending or {}).get("candidate_ip")
            self.store.update_fields(target_serial=serial)
            context["target_serial"] = serial
            next_state = "TARGET"
        elif action_id == "INSPECT-ACTION":
            identity = evidence.get("device_identity")
            if isinstance(identity, dict) and identity:
                self.store.update_fields(device_identity=identity)
                context["device_identity"] = identity
            installed_apps = evidence.get("installed_apps", {})
            self.store.update_fields(installed_apps=installed_apps)
            context["installed_apps"] = installed_apps
            next_state = "TASK"
            context["summary_rows"] = (
                {"status": "completed", "item": "目标电视盘点", "result": result},
            )
        elif action_id == "EMOTN-LAUNCH-ACTION":
            runtime = {
                "package": evidence.get("package"),
                "foreground": evidence.get("foreground"),
                "verified": True,
            }
            self.store.update_fields(emotn_runtime=runtime)
            context["emotn_runtime"] = runtime
            next_state = "LAUNCHER-RISK"
        elif action_id == "DANGBEI-ACTION":
            verified = {
                "app_id": "dangbei-market",
                "path": evidence.get("path"),
                "url": evidence.get("source_url"),
                **(evidence.get("file_identity") or {}),
            }
            files = [*context.get("verified_downloads", ()), verified]
            self.store.update_fields(verified_downloads=files, selected_apps=["dangbei-market"])
            context["verified_downloads"] = files
            context["selected_apps"] = ["dangbei-market"]
            context["download_rows"] = (
                {"status": "completed", "item": "当贝市场", "result": "官方包下载和身份校验完成"},
            )
            next_state = "DOWNLOAD-VERIFY"
        elif action_id == "DANGBEI-PAGE-ACTION":
            next_state = "DANGBEI-SOURCE"
            context["source_error"] = "已打开官网页面；包体身份仍未完成核验。"
        elif action_id == "DIAGNOSE-ACTION":
            next_state = "VERIFY"
            context["evidence_rows"] = (
                {"status": row_status, "item": "应用诊断", "result": result},
            )
        elif action_id == "DOWNLOAD-ACTION":
            files = list(evidence.get("files", ()))
            self.store.update_fields(verified_downloads=files)
            context["verified_downloads"] = files
            next_state = "DOWNLOAD-VERIFY"
            context["download_rows"] = (
                {"status": row_status, "item": "下载和包体验证", "result": result},
            )
        elif action_id == "PREPARE-INSTALL-PLAN-ACTION":
            plan = evidence["plan"]
            self.store.set_approved_plan(plan)
            context["approved_plan"] = plan
            next_state = "INSTALL-PLAN"
        elif action_id == "INSTALL-ACTION":
            installed = dict(context.get("installed_apps", {}))
            plan = (pending or {}).get("approved_plan") or {}
            app_ids = (
                [item.get("app_id") for item in plan.get("installations", ())]
                if plan.get("action") == "install_bundle"
                else [plan.get("app_id")]
            )
            for app_id in filter(None, app_ids):
                catalog_app = next((app for app in _load_catalog().get("apps", ()) if app.get("id") == app_id), {})
                installed[app_id] = catalog_app.get("version", "已安装")
            if any(app_ids):
                self.store.update_fields(installed_apps=installed)
                context["installed_apps"] = installed
            next_state = "VERIFY"
            context["evidence_rows"] = (
                {"status": row_status, "item": "应用安装", "result": result},
            )
        elif action_id == "HOME-ACTION":
            selected = tuple((pending or {}).get("selected_actions", ()))
            next_state = "WALLPAPER" if "wallpaper" in selected else "VERIFY"
            context["evidence_rows"] = (
                {"status": row_status, "item": "Home 键修改", "result": result},
            )
        elif action_id == "WALLPAPER-ACTION":
            next_state = "VERIFY"
            context["evidence_rows"] = (
                {"status": row_status, "item": "壁纸设置", "result": result},
            )
        else:
            raise AnswerError(f"不支持的操作结果：{action_id}")
        question = build_question(next_state, context)
        self.store.set_question(question)
        return {"accepted": True, "record": record, "question": question}
