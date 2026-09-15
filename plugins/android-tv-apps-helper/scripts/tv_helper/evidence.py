from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse
from .apk import validate_plan_id


SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _require(mapping: dict[str, Any], keys: tuple[str, ...], label: str) -> None:
    missing = [key for key in keys if mapping.get(key) in (None, "", [], {})]
    if missing:
        raise ValueError(f"{label}缺少证据字段：{', '.join(missing)}")


def _sha(value: Any, label: str) -> None:
    if not SHA256.fullmatch(str(value or "")):
        raise ValueError(f"{label}必须是 64 位小写 SHA-256。")


def _validate_failed(evidence: dict[str, Any]) -> None:
    _require(evidence, ("result",), "失败结果")
    if not any(evidence.get(key) not in (None, "", [], {}) for key in ("error", "exit_code", "exception", "observations")):
        raise ValueError("失败或注意状态必须包含 error、exit_code、exception 或 observations。")


def _argv_commands(value: Any, label: str) -> list[list[str]]:
    if not isinstance(value, list) or not value or not all(
        isinstance(command, list) and command and all(isinstance(token, str) and token for token in command)
        for command in value
    ):
        raise ValueError(f"{label}必须是非空 argv 命令数组。")
    return value


def _valid_plan(plan: dict[str, Any]) -> None:
    try:
        validate_plan_id(plan)
    except Exception as error:
        raise ValueError(f"安装计划摘要无效：{error}") from error


def validate_action_evidence(
    action_id: str,
    *,
    status: str,
    evidence: dict[str, Any],
    pending: dict[str, Any] | None,
) -> None:
    if not isinstance(evidence, dict) or not evidence:
        raise ValueError("操作结果必须包含可检查的 evidence。")
    if status != "completed":
        _validate_failed(evidence)
        return

    _require(evidence, ("result",), "完成结果")
    pending = pending or {}
    if action_id == "UPDATE-ACTION":
        package = evidence.get("package_validation")
        if not isinstance(package, dict):
            raise ValueError("Skill 更新必须包含 package_validation。")
        _require(package, ("skill_id", "version", "platform", "sha256"), "更新包校验")
        _sha(package["sha256"], "更新包摘要")
        expected = pending.get("update_check", {})
        if package["skill_id"] != "android-tv-apps-helper" or str(package["version"]) != str(expected.get("latest_version")):
            raise ValueError("更新包身份或版本与用户批准的新版本不一致。")
        if str(package["platform"]) != str(pending.get("host_platform")):
            raise ValueError("更新包平台与当前 Agent 平台不一致。")
        release = expected.get("release") or {}
        checksums = release.get("sha256sums") or {}
        platform = str(pending.get("host_platform"))
        expected_sha = release.get("expected_sha256") or expected.get("expected_sha256")
        if not expected_sha and isinstance(checksums, dict):
            candidates = [digest for name, digest in checksums.items() if f"-{platform}-" in str(name)]
            expected_sha = candidates[0] if len(candidates) == 1 else None
        if not expected_sha or package["sha256"] != expected_sha:
            raise ValueError("更新包摘要未与官方 Release SHA256SUMS 中的预期值匹配。")
        if evidence.get("installation_verified") is not True:
            raise ValueError("Skill 更新必须验证新版本已安装。")
        if evidence.get("previous_version_preserved_until_verified") is not True:
            raise ValueError("Skill 更新必须证明旧版本保留到新版本验证完成。")
    elif action_id == "ADB-VALIDATE-ACTION":
        _require(evidence, ("adb_path", "commands", "version", "exit_code", "precheck"), "ADB 工具验证")
        if evidence["exit_code"] != 0 or str(evidence["adb_path"]) != str(pending.get("adb_path")):
            raise ValueError("ADB 工具验证证据与用户填写的路径不一致。")
        flattened = " ".join(" ".join(map(str, command)) for command in evidence["commands"])
        if "version" not in flattened or "devices -l" not in flattened or " connect " in f" {flattened} ":
            raise ValueError("ADB 工具验证命令集合无效。")
    elif action_id == "PASSIVE-DISCOVERY-ACTION":
        precheck = evidence.get("precheck")
        commands = _argv_commands(evidence.get("commands"), "被动发现命令")
        if not isinstance(precheck, dict):
            raise ValueError("被动发现必须包含 precheck 和 commands。")
        _require(precheck, ("rows",), "被动发现")
        allowed_suffixes = {("version",), ("devices", "-l")}
        if any(tuple(command[1:]) not in allowed_suffixes for command in commands):
            raise ValueError("被动发现只能运行 adb version 和 adb devices -l。")
        if precheck.get("active_scan_performed") is not False:
            raise ValueError("被动发现不能标记为已执行主动扫描。")
    elif action_id == "CONNECT-ACTION":
        _require(evidence, ("target_serial", "endpoint", "command", "exit_code", "output"), "ADB 连接")
        endpoint = str(pending.get("candidate_ip"))
        serial = str(evidence["target_serial"])
        command = evidence["command"]
        if not isinstance(command, list) or command[-2:] != ["connect", endpoint]:
            raise ValueError("ADB 连接命令未绑定用户批准的地址。")
        if evidence["exit_code"] != 0 or str(evidence["endpoint"]) != endpoint or serial not in {endpoint, f"{endpoint}:5555"}:
            raise ValueError("ADB 连接证据与批准地址或成功退出码不匹配。")
    elif action_id == "SCAN-ACTION":
        _require(evidence, ("scope", "ports", "devices", "exit_code"), "有限扫描")
        approved = pending.get("scan_approval") or {}
        if evidence["exit_code"] != 0 or evidence["scope"] != approved.get("scope") or evidence["ports"] != approved.get("ports"):
            raise ValueError("有限扫描证据的范围、端口或退出码无效。")
    elif action_id == "INSPECT-ACTION":
        identity = evidence.get("device_identity")
        if not isinstance(identity, dict):
            raise ValueError("设备盘点必须包含 device_identity。")
        _require(identity, ("manufacturer", "model", "android_version", "sdk", "abi"), "设备身份")
        _require(evidence, ("target_serial", "commands", "exit_code"), "设备盘点")
        if evidence["exit_code"] != 0 or str(evidence["target_serial"]) != str(pending.get("target_serial")):
            raise ValueError("设备盘点证据与已确认目标不匹配。")
        if "installed_apps" not in evidence or not isinstance(evidence["installed_apps"], dict):
            raise ValueError("设备盘点必须包含 installed_apps 清单。")
    elif action_id == "EMOTN-LAUNCH-ACTION":
        _require(evidence, ("target_serial", "package", "foreground", "commands", "exit_code"), "Emotn UI 启动验证")
        if evidence["exit_code"] != 0 or str(evidence["target_serial"]) != str(pending.get("target_serial")):
            raise ValueError("Emotn UI 启动证据与已确认目标不匹配。")
        if evidence["package"] != "com.oversea.aslauncher" or str(evidence["package"]) not in str(evidence["foreground"]):
            raise ValueError("Emotn UI 启动证据未显示目标包位于前台。")
        installed = pending.get("installed_apps", {})
        if not installed.get("emotn-ui"):
            raise ValueError("Emotn UI 启动前没有已安装版本证据。")
    elif action_id == "DANGBEI-ACTION":
        identity = evidence.get("file_identity")
        if not isinstance(identity, dict):
            raise ValueError("当贝下载必须包含 file_identity。")
        _require(
            identity,
            ("package", "version_name", "version_code", "min_sdk", "abi", "signing_sha256", "size", "sha256"),
            "当贝包体身份",
        )
        _sha(identity["signing_sha256"], "当贝签名摘要")
        _sha(identity["sha256"], "当贝文件摘要")
        _require(evidence, ("source_url", "path"), "当贝来源")
        expected_app = pending.get("dangbei_expectation") or {}
        distribution = expected_app.get("distribution") or {}
        if distribution.get("verification_status") != "verified" or len(expected_app.get("assets", ())) != 1:
            raise ValueError("当贝目录尚无完整、已核验的固定包体身份，不能标记下载完成。")
        expected = expected_app["assets"][0]
        if evidence["source_url"] != expected.get("url") or identity.get("package") != distribution.get("expected_package"):
            raise ValueError("当贝来源或包名与固定官方目录不一致。")
        for field in ("size", "sha256", "signing_sha256", "version_name", "version_code", "min_sdk", "abi"):
            if identity.get(field) != expected.get(field):
                raise ValueError(f"当贝 {field} 与已核验目录不一致。")
    elif action_id == "DANGBEI-PAGE-ACTION":
        _require(evidence, ("publisher_url",), "当贝官网页面")
        if evidence.get("opened") is not True or urlparse(str(evidence["publisher_url"])).hostname not in {"www.dangbei.com", "dangbei.com"}:
            raise ValueError("当贝官网页面证据无效。")
    elif action_id == "DOWNLOAD-ACTION":
        files = evidence.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("下载完成必须包含逐文件 files 证据。")
        for item in files:
            _require(
                item,
                ("app_id", "path", "url", "size", "sha256", "package", "version_name", "version_code", "min_sdk", "abi", "signing_sha256", "exit_code"),
                "下载文件",
            )
            _sha(item["sha256"], "下载文件摘要")
            _sha(item["signing_sha256"], "下载签名摘要")
            if item["exit_code"] != 0:
                raise ValueError("下载文件校验退出码不是成功。")
        if set(pending.get("selected_apps", ())) != {str(item["app_id"]) for item in files}:
            raise ValueError("下载文件清单与用户确认的应用清单不一致。")
        expected_by_id = {item["app_id"]: item for item in pending.get("download_expectations", ())}
        for item in files:
            expected = expected_by_id.get(item["app_id"])
            if not expected:
                raise ValueError("下载文件没有对应的目录预期。")
            for field in ("url", "size", "sha256", "package", "version_name"):
                if expected.get(field) not in (None, "") and item.get(field) != expected.get(field):
                    raise ValueError(f"下载文件 {field} 与用户批准的固定目录不一致。")
    elif action_id == "PREPARE-INSTALL-PLAN-ACTION":
        plan = evidence.get("plan")
        if not isinstance(plan, dict) or plan.get("status") != "planned":
            raise ValueError("安装计划准备必须回传 planned 计划。")
        _valid_plan(plan)
        if str(plan.get("serial")) != str(pending.get("target_serial")):
            raise ValueError("安装计划未绑定已确认电视。")
        expected = {(item["app_id"], item["sha256"]) for item in pending.get("verified_downloads", ())}
        if plan.get("action") == "install_bundle":
            actual = {(item.get("app_id"), (item.get("apk") or {}).get("sha256")) for item in plan.get("installations", ())}
        else:
            actual = {(plan.get("app_id"), (plan.get("apk") or {}).get("sha256"))}
        if not expected or actual != expected:
            raise ValueError("安装计划与已验证下载文件清单不一致。")
    elif action_id == "INSTALL-ACTION":
        installs = evidence.get("installations")
        if not isinstance(installs, list) or not installs:
            raise ValueError("安装完成必须包含逐应用 installations 证据。")
        plan = pending.get("approved_plan") or {}
        if plan.get("status") != "approved" or not plan.get("plan_id"):
            raise ValueError("安装动作没有绑定经用户批准的不可变计划。")
        _valid_plan(plan)
        if plan.get("action") == "install_bundle":
            plan_items = {
                item.get("app_id"): (item.get("apk") or {}).get("sha256")
                for item in plan.get("installations", ())
            }
        else:
            plan_items = {plan.get("app_id"): (plan.get("apk") or {}).get("sha256")}
        if len(installs) != len(plan_items):
            raise ValueError("安装结果数量与批准计划不一致。")
        for item in installs:
            _require(item, ("app_id", "target_serial", "apk_sha256", "plan_id", "exit_code", "output"), "安装结果")
            _sha(item["apk_sha256"], "安装 APK 摘要")
            if item["exit_code"] != 0 or "success" not in str(item["output"]).casefold():
                raise ValueError("安装证据不包含成功退出码和 Success 输出。")
            if str(item["target_serial"]) != str(pending.get("target_serial")):
                raise ValueError("安装证据的目标设备与批准计划不一致。")
            if item["app_id"] not in plan_items or item["plan_id"] != plan.get("plan_id") or item["apk_sha256"] != plan_items[item["app_id"]]:
                raise ValueError("安装结果与用户批准的应用、计划或 APK 摘要不一致。")
    elif action_id == "DIAGNOSE-ACTION":
        _require(evidence, ("target_serial", "commands", "observations", "exit_code"), "应用诊断")
        if evidence["exit_code"] != 0 or str(evidence["target_serial"]) != str(pending.get("target_serial")):
            raise ValueError("诊断证据与已确认目标不匹配。")
    elif action_id == "HOME-ACTION":
        _require(evidence, ("target_serial", "before_home", "after_home", "verification_command", "exit_code"), "Home 键修改")
        if evidence["exit_code"] != 0 or evidence["before_home"] == evidence["after_home"]:
            raise ValueError("Home 键完成证据未显示实际生效变化。")
        if str(evidence["target_serial"]) != str(pending.get("target_serial")):
            raise ValueError("Home 键证据的目标设备不匹配。")
        expected_home = str(pending.get("expected_home_package"))
        if expected_home not in str(evidence["after_home"]):
            raise ValueError("Home 键修改后的桌面不是用户批准的 Emotn UI。")
        runtime = pending.get("emotn_runtime", {})
        if "home_key" not in pending.get("selected_actions", ()) or runtime.get("verified") is not True or runtime.get("package") != expected_home:
            raise ValueError("Home 键修改缺少用户选择或 Emotn UI 前台验证。")
    elif action_id == "WALLPAPER-ACTION":
        _require(evidence, ("target_serial", "asset_identity", "verification_result", "exit_code"), "壁纸设置")
        if evidence["exit_code"] != 0 or str(evidence["target_serial"]) != str(pending.get("target_serial")):
            raise ValueError("壁纸证据的目标设备或退出码不匹配。")
        asset = evidence["asset_identity"]
        if not isinstance(asset, dict) or not (asset.get("kind") == "default" or SHA256.fullmatch(str(asset.get("sha256", "")))):
            raise ValueError("壁纸资源身份必须是默认资源或有效 SHA-256。")
        approved = pending.get("wallpaper_asset") or {}
        if approved.get("kind") == "default":
            matches = asset.get("kind") == "default"
        else:
            matches = approved.get("sha256") and approved.get("sha256") == asset.get("sha256")
        runtime = pending.get("emotn_runtime", {})
        if not matches or runtime.get("verified") is not True or runtime.get("package") != "com.oversea.aslauncher":
            raise ValueError("壁纸证据与用户批准的资源或 Emotn UI 前台验证不一致。")
    elif action_id == "FINISH-CHECK":
        _require(evidence, ("command",), "ADB 关闭复核")
        if evidence.get("check_performed") is not True or not isinstance(evidence.get("adb_still_reachable"), bool):
            raise ValueError("ADB 关闭复核必须包含实际检查标记和布尔型可达结果。")
        target = pending.get("target_serial")
        if target and str(target) not in " ".join(map(str, evidence["command"])):
            raise ValueError("ADB 关闭复核命令未绑定已确认目标。")
    else:
        raise ValueError(f"不支持的操作结果：{action_id}")
