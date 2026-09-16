import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'plugins/android-tv-apps-helper/scripts'))
from tv_helper.session import SessionStore
from tv_helper.workflow import build_question
from tv_helper.html_ui import HtmlController


class HtmlServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        store = SessionStore.create(Path(self.tmp.name)/'session.json', interaction_surface='html')
        store.set_question(build_question('PRECHECK_WIFI', {}))
        from tv_helper.html_server import ChoiceServer
        self.server = ChoiceServer(HtmlController(store))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, path, payload=None, headers=None):
        request = urllib.request.Request(self.base+path, data=json.dumps(payload).encode() if payload is not None else None,
            headers=headers if headers is not None else {'Authorization': 'Bearer '+self.server.token, 'Content-Type':'application/json', 'Origin':self.base})
        try:
            with urllib.request.urlopen(request, timeout=3) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_state_requires_secret_and_no_remote_origin(self):
        self.assertEqual(self.request('/state', headers={})[0], 403)
        self.assertEqual(self.request('/state', headers={'Authorization':'Bearer '+self.server.token,'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.request('/state', headers={'Authorization':'Bearer '+self.server.token,'Host':'evil.example'})[0],403)
        self.assertEqual(self.request('/state')[0],200)

    def test_http_click_updates_same_session_and_rejects_replay(self):
        initial=json.loads(self.request('/state')[1])
        view=initial['presentation']
        payload={'question_id':view['question_id'],'presentation_id':view['presentation_id'],'values':['same_wifi']}
        code, body=self.request('/answer', payload)
        self.assertEqual(code,200)
        self.assertEqual(json.loads(body)['presentation']['question_id'],'PRECHECK-ADB-Q1')
        self.assertEqual(self.request('/answer',payload)[0],409)
        self.assertTrue(self.server.controller.wait(initial['revision'],0)['changed'])

    def test_shell_is_served_without_disclosing_state_or_token(self):
        code, body=self.request('/',headers={})
        self.assertEqual(code,200)
        self.assertIn(b'<!doctype html>',body.lower())
        self.assertNotIn(self.server.token.encode(),body)
        self.assertEqual(self.request('/../../session.json')[0],404)


if __name__=='__main__': unittest.main()
