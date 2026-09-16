import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'plugins/android-tv-apps-helper/scripts'))
from tv_helper.catalog import load_catalog, validate_catalog, eligible_downloads
from tv_helper.downloads import app_selection_rows
from tv_helper.workflow import build_question, WorkflowEngine, _download_expectations
from tv_helper.session import SessionStore
from tv_helper.evidence import validate_action_evidence


class AppChoiceAvailabilityTests(unittest.TestCase):
    def test_install_confirmation_and_result_use_actual_downloaded_version(self):
        import hashlib
        import zipfile
        from tv_helper.apk import create_install_bundle_plan
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / 'emotn.apk'
            with zipfile.ZipFile(apk, 'w') as archive:
                archive.writestr('AndroidManifest.xml', 'fixture')
            file = {'app_id': 'emotn-ui', 'path': str(apk), 'sha256': hashlib.sha256(apk.read_bytes()).hexdigest(), 'version_name': '99.99'}
            plan = create_install_bundle_plan(serial='fixture-tv', verified_downloads=[file])
            store = SessionStore.create(Path(tmp) / 'session.json', interaction_surface='auto')
            store.update_fields(verified_downloads=[file], target_serial='fixture-tv', selected_apps=['emotn-ui'])
            store.set_approved_plan(plan)
            question = build_question('INSTALL-PLAN', store.read())
            self.assertIn('99.99', str(question.summary_rows))
            self.assertTrue(any(row['status'] == 'attention' and '1.1.0.1' in row['result'] for row in question.summary_rows))
            store.set_question(question)
            engine = WorkflowEngine(store)
            result = engine.submit('approve_install', question_id=question.question_id)
            self.assertTrue(result['accepted'])
            engine.record_action('INSTALL-ACTION', status='completed', evidence={'result': 'installed', 'installations': [{'app_id': 'emotn-ui', 'target_serial': 'fixture-tv', 'apk_sha256': file['sha256'], 'plan_id': plan['plan_id'], 'exit_code': 0, 'output': 'Success'}]})
            self.assertEqual(store.read()['installed_apps']['emotn-ui'], '99.99')

    def setUp(self):
        self.catalog = load_catalog(ROOT / 'plugins/android-tv-apps-helper/catalog/apps.json')

    def test_every_catalog_app_is_selectable_without_source_approval(self):
        question = build_question('APPS', {})
        selectable = {o.value for o in question.options if o.enabled}
        self.assertTrue({app['id'] for app in self.catalog['apps']} <= selectable)
        self.assertTrue(all(row['enabled'] for row in app_selection_rows(self.catalog['apps'], {})))

    def test_all_apps_reachable_in_each_hosts_native_pages(self):
        from tv_helper.presentation import build_host_presentation
        from tv_helper.questions import Question
        wanted = {app['id'] for app in self.catalog['apps']}
        for platform in ('codex', 'workbuddy', 'doubao-work', 'claude'):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as tmp:
                store = SessionStore.create(Path(tmp) / 'session.json', interaction_surface='auto', host_platform=platform)
                store.set_question(build_question('APPS', {}))
                seen = set()
                for _ in range(20):
                    data = store.read()
                    view = build_host_presentation(Question.from_dict(data['pending_question']), data)
                    seen.update(value.removeprefix('ui:toggle:') for value in view['answer_value_map'].values())
                    if wanted <= seen:
                        break
                    WorkflowEngine(store).submit_native('ui:next', question_id=view['question_id'], presentation_id=view['presentation_id'])
                self.assertTrue(wanted <= seen)
                self.assertIsNone(store.read()['pending_action'])

    def test_dangbei_retry_accepts_file_without_maintainer_preaudit(self):
        app = next(a for a in self.catalog['apps'] if a['id'] == 'dangbei-market')
        identity = {'package': 'com.dangbeimarket', 'version_name': '6.0.7', 'version_code': '613', 'min_sdk': 21, 'abi': 'armeabi-v7a', 'signing_sha256': 'b'*64, 'size': 123, 'sha256': 'a'*64}
        validate_action_evidence('DANGBEI-ACTION', status='completed', evidence={'result': 'downloaded', 'path': '/tmp/test.apk', 'source_url': app['distribution']['resolved_url'], 'file_identity': identity}, pending={'dangbei_expectation': app})

    def test_pending_source_url_is_download_eligible_without_preaudited_hash(self):
        app = copy.deepcopy(next(a for a in self.catalog['apps'] if a['id'] == 'jiashitong'))
        app['distribution']['url'] = 'https://example.com/tv.apk'
        catalog = {'schema_version': 1, 'apps': [app]}
        validate_catalog(catalog)
        self.assertEqual([a['id'] for a in eligible_downloads(catalog)], ['jiashitong'])

    def test_unreviewed_apps_reach_named_confirmation_and_download_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore.create(Path(tmp) / 'session.json', interaction_surface='auto')
            store.set_question(build_question('APPS', {}))
            engine = WorkflowEngine(store)
            result = engine.submit('dangbei-market,emotn-ui,jiashitong', question_id='APPS-Q1')
            self.assertTrue(result['accepted'])
            self.assertIn('当贝市场', result['question'].prompt)
            self.assertIn('Emotn UI', result['question'].prompt)
            self.assertIn('佳视通', result['question'].prompt)
            result = engine.submit('confirm_download', question_id='DOWNLOAD-CONFIRM-Q1')
            self.assertTrue(result['accepted'])
            self.assertEqual(store.read()['pending_action']['action_id'], 'DOWNLOAD-ACTION')
            expectations = store.read()['pending_action']['download_expectations']
            self.assertEqual(len(expectations), 3)
            missing = next(item for item in expectations if item['app_id'] == 'jiashitong')
            self.assertTrue(missing['resolve_required'])

    def test_file_evidence_accepts_unreviewed_source_but_rejects_wrong_known_package(self):
        expected = _download_expectations(('dangbei-market',))
        file = {'app_id': 'dangbei-market', 'path': '/tmp/test.apk', 'url': expected[0]['url'], 'size': 123, 'sha256': 'a'*64, 'package': 'com.dangbeimarket', 'version_name': '6.0.7', 'version_code': '613', 'min_sdk': 21, 'abi': 'armeabi-v7a', 'signing_sha256': 'b'*64, 'exit_code': 0}
        pending = {'selected_apps': ['dangbei-market'], 'download_expectations': expected}
        validate_action_evidence('DOWNLOAD-ACTION', status='completed', evidence={'result': 'downloaded', 'files': [file]}, pending=pending)
        with self.assertRaises(ValueError):
            validate_action_evidence('DOWNLOAD-ACTION', status='completed', evidence={'result': 'downloaded', 'files': [{**file, 'package': 'wrong.app'}]}, pending=pending)
