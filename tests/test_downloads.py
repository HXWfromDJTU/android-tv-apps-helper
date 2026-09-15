import unittest

from tv_helper.downloads import (
    DownloadError,
    app_selection_rows,
    named_download_confirmation,
    redirect_allowed,
    validate_download_identity,
)


class DownloadTests(unittest.TestCase):
    def test_named_confirmation_resolves_names_and_versions(self):
        apps = [
            {"id": "a", "name": "软件 A", "version": "1.0", "distribution": {"mode": "upstream_release"}, "assets": [{}]},
            {"id": "b", "name": "软件 B", "version": "2.0", "distribution": {"mode": "project_release"}, "assets": [{}]},
        ]
        confirmation = named_download_confirmation(apps, ("a", "b"))
        self.assertEqual(confirmation["display_names"], ("软件 A 1.0", "软件 B 2.0"))
        self.assertEqual(confirmation["question_id"], "DOWNLOAD-CONFIRM-Q1")

    def test_unavailable_apps_are_visible_but_disabled(self):
        rows = app_selection_rows(
            [
                {"id": "emotn", "name": "Emotn UI", "version": "1.1", "purpose": "电视桌面", "distribution": {"mode": "pending_rights", "reason": "未获授权"}, "assets": []}
            ],
            installed={},
        )
        self.assertFalse(rows[0]["enabled"])
        self.assertIn("未获授权", rows[0]["availability"])

    def test_official_redirect_must_stay_on_allowlist(self):
        allowed = ("www.dangbei.com", "app.qingyingyong.net", "apk.znds.com")
        self.assertTrue(redirect_allowed("https://app.qingyingyong.net/file.apk", allowed))
        self.assertFalse(redirect_allowed("https://example.invalid/file.apk", allowed))

    def test_download_identity_rejects_package_or_signature_change(self):
        expected = {
            "package": "com.dangbeimarket",
            "version_name": "6.0.7",
            "version_code": "607",
            "min_sdk": 21,
            "abi": "armeabi-v7a",
            "signing_sha256": "a" * 64,
            "size": 123,
            "sha256": "c" * 64,
        }
        with self.assertRaisesRegex(DownloadError, "package"):
            validate_download_identity(expected, {**expected, "package": "evil.example"})
        with self.assertRaisesRegex(DownloadError, "signing_sha256"):
            validate_download_identity(expected, {**expected, "signing_sha256": "b" * 64})
        for field, wrong in (("version_code", "999"), ("min_sdk", 99), ("abi", "x86")):
            with self.subTest(field=field), self.assertRaisesRegex(DownloadError, field):
                validate_download_identity(expected, {**expected, field: wrong})


if __name__ == "__main__":
    unittest.main()
