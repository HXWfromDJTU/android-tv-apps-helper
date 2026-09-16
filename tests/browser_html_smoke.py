"""Real Chromium click tests; explicit opt-in script, no physical TV operations."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

sys.path.insert(0, str(Path(__file__).parents[1]/'plugins/android-tv-apps-helper/scripts'))
from tv_helper.session import SessionStore
from tv_helper.workflow import build_question
from tv_helper.html_ui import HtmlController, html_document
from tv_helper.html_server import ChoiceServer


class BrowserClickTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        cls.browser=cls.pw.chromium.launch(channel='chrome',headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=SessionStore.create(Path(self.tmp.name)/'session.json',interaction_surface='html')
        self.ui=HtmlController(self.store)
        self.server=ChoiceServer(self.ui)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.page=self.browser.new_page(viewport={'width':900,'height':740})
        self.addCleanup(self.stop)

    def stop(self):
        self.page.close(); self.server.shutdown(); self.server.server_close(); self.thread.join()

    def start(self,state):
        self.store.set_question(build_question(state,self.store.read()))
        self.page.goto(self.server.url)
        expect(self.page.locator('#options input').first).to_be_visible()

    def choose(self,value):
        self.page.locator(f'#options input[value="{value}"]').check()
        self.page.locator('#submit').click()

    def test_unstarted_session_is_not_reported_complete(self):
        self.page.goto(self.server.url)
        expect(self.page.locator('#question')).to_have_text('等待 Agent 准备当前问题')
        expect(self.page.locator('#waiting')).not_to_contain_text('任务结果已保存')

    def test_two_round_click_and_agent_wait_receives_approved_action(self):
        self.start('PRECHECK_WIFI')
        revision=self.ui.snapshot()['revision']
        expect(self.page.locator('#submit')).to_be_disabled()
        self.choose('same_wifi')
        expect(self.page.locator('#question')).to_contain_text('电视是否已开启')
        self.assertTrue(self.ui.wait(revision,0)['changed'])
        self.choose('adb_enabled')
        expect(self.page.locator('#waiting')).to_contain_text('已保存你的选择')
        self.assertEqual(self.store.read()['pending_action']['action_id'],'PASSIVE-DISCOVERY-ACTION')
        self.assertEqual(self.store.read()['evidence_records'],[])

    def test_full_multiselect_sticky_confirm_and_reload(self):
        self.start('APPS')
        self.assertGreater(self.page.locator('#options input').count(),4)
        self.page.locator('input[value="clash-meta"]').check()
        self.page.locator('input[value="smarttube"]').check()
        expect(self.page.locator('#selected-apps')).to_contain_text('SmartTube')
        expect(self.page.locator('#submit')).to_have_text('确认所选应用，进入安装流程')
        self.page.evaluate('window.scrollTo(0,0)')
        bounds = self.page.locator('#submit').bounding_box()
        self.assertGreaterEqual(bounds['y'], 0)
        self.assertLessEqual(bounds['y']+bounds['height'], 740)
        self.page.reload()
        expect(self.page.locator('input[value="smarttube"]')).to_be_checked()
        self.assertEqual(self.page.locator('#actions').evaluate('(e)=>getComputedStyle(e).position'),'fixed')
        self.page.locator('#submit').click()
        expect(self.page.locator('#question')).to_contain_text('下载')
        expect(self.page.locator('#context')).to_contain_text('SmartTube')
        self.assertIsNone(self.store.read()['pending_action'])

    def test_invalid_input_stays_and_recovers_by_click(self):
        self.start('ADB-SETUP')
        expect(self.page.locator('#input-area')).to_be_hidden()
        self.choose('ui:input')
        expect(self.page.locator('#input-area')).to_be_visible()
        self.page.locator('#input').fill('relative-path')
        self.choose('ui:submit_input')
        expect(self.page.locator('#error')).to_contain_text('绝对路径')
        self.page.locator('#input').fill('/tmp/example-adb')
        self.choose('ui:submit_input')
        expect(self.page.locator('#waiting')).to_be_visible()
        self.assertEqual(self.store.read()['pending_action']['action_id'],'ADB-VALIDATE-ACTION')

    def test_embedded_bridge_simulation_clicks_and_message_array(self):
        """Simulated host only: not Codex/WorkBuddy/Doubao client acceptance."""
        import json
        self.store.set_question(build_question('APPS', self.store.read()))
        def harness(source, params):
            if params['name'] == 'tv_ui_submit':
                return {'structuredContent': {**self.ui.submit(params['arguments']['payload']), 'session_key':'test'}}
            return {'contents':[{'text':json.dumps({**self.ui.snapshot(),'session_key':'test'})}]}
        self.page.expose_binding('callHarness', harness)
        self.page.set_content('<iframe id="app" style="width:880px;height:740px;border:0"></iframe>')
        self.page.evaluate('''({html,state}) => {
          window.messages=[];
          const frame=document.getElementById('app');
          window.addEventListener('message', async ({data:m,source})=>{
            if(source!==frame.contentWindow || !m.method) return;
            let result={};
            if(m.method==='ui/initialize') result={protocolVersion:'2026-01-26',hostInfo:{name:'test-host',version:'1'},hostCapabilities:{}};
            else if(m.method==='tools/call') result=await window.callHarness(m.params);
            else if(m.method==='resources/read') result=await window.callHarness({name:'read'});
            else if(m.method==='ui/message') window.messages.push(m.params);
            else if(m.method==='ui/notifications/size-changed') frame.style.height=m.params.height+'px';
            if(m.id) source.postMessage({jsonrpc:'2.0',id:m.id,result},'*');
            if(m.method==='ui/notifications/initialized') source.postMessage({jsonrpc:'2.0',method:'ui/notifications/tool-result',params:{structuredContent:{...state,session_key:'test'}}},'*');
          });
          frame.srcdoc=html;
        }''', {'html':html_document(),'state':self.ui.snapshot()})
        ui=self.page.frame_locator('#app')
        ui.locator('input[value="clash-meta"]').check()
        ui.locator('input[value="smarttube"]').check()
        ui.locator('input[value="emotn-ui"]').check()
        ui.locator('body').evaluate('(e)=>window.scrollTo(0,0)')
        self.assertTrue(ui.locator('#submit').evaluate('(e)=>{const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight}'))
        self.assertLessEqual(self.page.locator('#app').evaluate('(e)=>e.getBoundingClientRect().height'),740)
        ui.locator('#submit').click()
        expect(ui.locator('#question')).to_contain_text('下载')
        self.page.wait_for_function('window.messages.length===1')
        messages=self.page.evaluate('window.messages')
        self.assertIsInstance(messages[0]['content'],list)
        self.assertIsNone(self.store.read()['pending_action'])


if __name__=='__main__':unittest.main()
