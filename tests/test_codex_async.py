import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'plugins/android-tv-apps-helper/scripts'))
from tv_helper.session import SessionStore
from tv_helper.workflow import WorkflowEngine, build_question
from tv_helper.presentation import build_host_presentation
from tv_helper.questions import Question, AnswerError


class CodexAsyncTests(unittest.TestCase):
    def test_async_preserves_choice_consequences_outside_short_title(self):
        question = build_question('DIAGNOSE', {})
        view = build_host_presentation(question, {'host_platform': 'codex', 'native_tool': 'request_user_input_async'})
        payload = view['tool_input']['questions'][0]
        self.assertEqual(payload['title'], question.component_prompt())
        self.assertIn('启动日志', view['context_markdown'])
        for option in question.options:
            if option.description and option.value in view['answer_value_map'].values():
                self.assertIn(option.description, view['context_markdown'])

    def test_all_async_questions_fit_schema_and_visible_answer_map(self):
        from tv_helper.workflow import WORKFLOW_STATES
        for state in WORKFLOW_STATES:
            with self.subTest(state=state):
                question = build_question(state, {})
                view = build_host_presentation(question, {'host_platform': 'codex', 'native_tool': 'request_user_input_async'})
                payload = view['tool_input']['questions'][0]
                self.assertEqual(set(payload), {'title', 'options'})
                self.assertTrue(2 <= len(payload['options']) <= 3)
                self.assertTrue(all(option in view['answer_value_map'] for option in payload['options']))

    def test_cli_can_resume_existing_checkpoint_with_async_tool(self):
        cli = ROOT / 'plugins/android-tv-apps-helper/scripts/tv-helper'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'session.json'
            result = subprocess.run([sys.executable, str(cli), 'init-session', str(path), '--surface', 'auto', '--native-tool', 'request_user_input_async'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            store = SessionStore(path)
            self.assertEqual(store.read()['native_tool'], 'request_user_input_async')
            question = build_question('PRECHECK_WIFI', {})
            store.set_question(question)
            result = subprocess.run([sys.executable, str(cli), 'resume-native', str(path), '--question-id', question.question_id, '--native-tool', 'request_user_input_async'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['presentation']['tool_name'], 'request_user_input_async')

    def test_async_schema_and_reply_advance_only_after_explicit_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore.create(Path(tmp) / 'session.json', interaction_surface='auto', native_tool='request_user_input_async')
            question = build_question('PRECHECK_WIFI', {})
            store.set_question(question)
            view = build_host_presentation(question, store.read())
            self.assertEqual(view['tool_name'], 'request_user_input_async')
            payload = view['tool_input']['questions'][0]
            self.assertEqual(set(payload), {'title', 'options'})
            self.assertTrue(all(isinstance(option, str) for option in payload['options']))
            self.assertEqual(view['response_delivery'], 'async_user_message')
            self.assertEqual(store.read()['history'], [])
            label = next(label for label in payload['options'] if view['answer_value_map'][label] == 'same_wifi')
            result = WorkflowEngine(store).submit_native(label, question_id=view['question_id'], presentation_id=view['presentation_id'])
            self.assertTrue(result['accepted'])
            self.assertEqual(result['question'].question_id, 'PRECHECK-ADB-Q1')

    def test_switch_from_blocked_sync_preserves_question_and_invalidates_old_callback(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore.create(Path(tmp) / 'session.json', interaction_surface='auto')
            question = build_question('DISCOVERY-NONE', {})
            store.set_question(question)
            before = store.read()
            old = build_host_presentation(question, before)
            store.record_surface_failure(reason='native_tool_not_exposed', detail='Plan only', question_id=old['question_id'], presentation_id=old['presentation_id'], tool_name=old['tool_name'])
            store.resume_native(question.question_id, native_tool='request_user_input_async')
            after = store.read()
            view = build_host_presentation(question, after)
            self.assertEqual(after['pending_question'], before['pending_question'])
            self.assertEqual(after['history'], [])
            self.assertEqual(view['mode'], 'native_required')
            self.assertEqual(view['tool_name'], 'request_user_input_async')
            with self.assertRaises(AnswerError):
                WorkflowEngine(store).submit_native('safe_exit', question_id=old['question_id'], presentation_id=old['presentation_id'])
            WorkflowEngine(store).submit_native('ui:next', question_id=view['question_id'], presentation_id=view['presentation_id'])
            self.assertEqual(build_host_presentation(question, store.read())['tool_name'], 'request_user_input_async')

    def test_cross_platform_tool_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                SessionStore.create(Path(tmp) / 'session.json', interaction_surface='auto', host_platform='workbuddy', native_tool='request_user_input_async')

    def test_codex_zip_contains_resolvable_icon_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'codex.zip'
            subprocess.run([sys.executable, str(ROOT / 'scripts/build_platform_packages.py'), '--platform', 'codex', '--output', str(path)], check=True, capture_output=True)
            with zipfile.ZipFile(path) as package:
                root = 'android-tv-apps-helper/'
                self.assertIn(root + 'agents/openai.yaml', package.namelist())
                metadata = package.read(root + 'agents/openai.yaml').decode()
                for line in metadata.splitlines():
                    if 'icon_small:' in line or 'icon_large:' in line:
                        relative = line.split(':', 1)[1].strip().strip('"').removeprefix('./')
                        self.assertNotIn('..', relative)
                        self.assertTrue(package.read(root + relative).startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertIn('icon_small:', metadata)
                self.assertIn('icon_large:', metadata)
