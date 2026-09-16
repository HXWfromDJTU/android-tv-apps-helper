import json
import multiprocessing
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'plugins/android-tv-apps-helper/scripts'))
from tv_helper.session import SessionStore
from tv_helper.workflow import WorkflowEngine, build_question
from tv_helper.questions import AnswerError
from tv_helper.presentation import build_host_presentation


def submit_process(path, barrier, payload, queue):
    from tv_helper.html_ui import HtmlController
    ui = HtmlController(SessionStore(path))
    barrier.wait(timeout=10)
    try:
        queue.put(('accepted', ui.submit(payload)['accepted']))
    except AnswerError:
        queue.put(('stale', False))
    except Exception as error:
        queue.put(('error', repr(error)))


class HtmlChoiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'session.json'

    def create(self, platform='codex', state='PRECHECK_WIFI'):
        store = SessionStore.create(self.path, interaction_surface='html', host_platform=platform)
        store.set_question(build_question(state, store.read()))
        return store

    def controller(self, store):
        from tv_helper.html_ui import HtmlController
        return HtmlController(store)

    def submit(self, controller, values, **extra):
        view = controller.snapshot()['presentation']
        return controller.submit({'question_id': view['question_id'], 'presentation_id': view['presentation_id'], 'values': values, **extra})

    def test_four_desktop_hosts_can_use_html_but_claude_code_stays_native(self):
        for platform in ('codex', 'claude-desktop', 'workbuddy', 'doubao-work'):
            with self.subTest(platform=platform):
                store = self.create(platform)
                self.assertEqual(self.controller(store).snapshot()['presentation']['mode'], 'html_required')
        for platform in ('claude',):
            with self.subTest(platform=platform), self.assertRaises(ValueError):
                self.create(platform)

    def test_click_advances_and_duplicate_is_rejected(self):
        store = self.create()
        ui = self.controller(store)
        old = ui.snapshot()['presentation']
        result = self.submit(ui, ['same_wifi'])
        self.assertTrue(result['accepted'])
        self.assertEqual(result['presentation']['question_id'], 'PRECHECK-ADB-Q1')
        with self.assertRaises(AnswerError):
            ui.submit({'question_id': old['question_id'], 'presentation_id': old['presentation_id'], 'values': ['same_wifi']})
        self.assertEqual(len(store.read()['history']), 1)

    def test_supplemental_note_is_preserved_but_does_not_authorize_extra_actions(self):
        store = self.create()
        ui = self.controller(store)
        result = self.submit(ui, ['same_wifi'], note='我不知道电视型号，请先帮我识别。')
        self.assertEqual(result['latest_answer']['note'], '我不知道电视型号，请先帮我识别。')
        self.assertIsNone(result['action_required'])

    def test_no_selection_or_unrecognized_selection_never_advances(self):
        store = self.create()
        ui = self.controller(store)
        for values in ([], ['1'], ['invented'], ['same_wifi', 'different_wifi']):
            with self.subTest(values=values), self.assertRaises(AnswerError):
                self.submit(ui, values)
        self.assertEqual(store.read()['history'], [])

    @unittest.skipUnless(os.name == 'posix', 'fork concurrency test')
    def test_two_transports_cannot_accept_the_same_click_concurrently(self):
        store = self.create()
        view = self.controller(store).snapshot()['presentation']
        payload = {'question_id':view['question_id'], 'presentation_id':view['presentation_id'], 'values':['same_wifi']}
        ctx = multiprocessing.get_context('fork')
        barrier, queue = ctx.Barrier(4), ctx.Queue()
        processes = [ctx.Process(target=submit_process,args=(self.path,barrier,payload,queue)) for _ in range(4)]
        for process in processes: process.start()
        results = [queue.get(timeout=10) for _ in processes]
        for process in processes: process.join(timeout=10)
        self.assertEqual(results.count(('accepted',True)),1,results)
        self.assertEqual(results.count(('stale',False)),3,results)
        self.assertEqual(len(store.read()['history']),1)

    def test_multi_select_has_full_catalog_and_named_confirmation(self):
        store = self.create(state='APPS')
        ui = self.controller(store)
        options = ui.snapshot()['presentation']['options']
        self.assertGreater(len(options), 4)
        apps = [o['value'] for o in options if o['next_state'] == 'DOWNLOAD-CONFIRM'][:2]
        self.assertEqual(len(apps), 2)
        result = self.submit(ui, apps)
        self.assertEqual(result['presentation']['question_id'], 'DOWNLOAD-CONFIRM-Q1')
        self.assertIsNone(result['action_required'])
        for value in apps:
            name = next(o['label'] for o in options if o['value'] == value)
            self.assertIn(name, json.dumps(result, ensure_ascii=False))

    def test_short_text_requires_click_to_open_input_then_validated_value(self):
        store = self.create(state='ADB-SETUP')
        ui = self.controller(store)
        with self.assertRaises(AnswerError):
            self.submit(ui, ['ui:input'], text='/tmp/adb')
        self.submit(ui, ['ui:input'])
        self.assertTrue(ui.snapshot()['presentation']['accepts_free_input'])
        invalid = self.submit(ui, ['ui:submit_input'], text='not-absolute')
        self.assertFalse(invalid['accepted'])
        self.assertEqual(invalid['presentation']['question_id'], 'ADB-SETUP-Q1')
        result = self.submit(ui, ['ui:submit_input'], text='/tmp/adb')
        self.assertEqual(result['action_required']['action_id'], 'ADB-VALIDATE-ACTION')
        self.assertIsNone(result['presentation'])
        self.assertEqual(store.read()['evidence_records'], [])

    def test_native_hosts_keep_native_controls(self):
        for platform in ('claude', 'workbuddy', 'doubao-work'):
            store = SessionStore.create(self.path, interaction_surface='auto', host_platform=platform)
            q = build_question('PRECHECK_WIFI', {})
            view = build_host_presentation(q, store.read())
            self.assertEqual(view['tool_name'], 'AskUserQuestion')
            self.assertEqual(view['mode'], 'native_required')

    def test_resume_html_preserves_blocked_question_but_invalidates_token(self):
        store = SessionStore.create(self.path, interaction_surface='auto', host_platform='codex')
        store.set_question(build_question('PRECHECK_WIFI', {}))
        old = build_host_presentation(build_question('PRECHECK_WIFI', {}), store.read())
        store.resume_html('PRECHECK-WIFI-Q1')
        ui = self.controller(store)
        self.assertEqual(ui.snapshot()['presentation']['question_id'], old['question_id'])
        self.assertNotEqual(ui.snapshot()['presentation']['presentation_id'], old['presentation_id'])


if __name__ == '__main__':
    unittest.main()
