import asyncio
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS=Path(__file__).parents[1]/'plugins/android-tv-apps-helper/scripts'
sys.path.insert(0,str(SCRIPTS))
from tv_helper.session import SessionStore
from tv_helper.workflow import build_question


class HtmlCliTests(unittest.TestCase):
    def test_cli_init_and_wait_return_html_state_without_plan_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'session.json'
            result=subprocess.run([sys.executable,str(SCRIPTS/'tv-helper'),'init-session',str(path),'--surface','html','--host-platform','claude-desktop'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            SessionStore(path).set_question(build_question('PRECHECK_WIFI',{}))
            result=subprocess.run([sys.executable,str(SCRIPTS/'tv-helper'),'wait-ui',str(path),'--after','initial','--timeout','0'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['presentation']['mode'],'html_required')

    @unittest.skipUnless(importlib.util.find_spec('mcp'),'optional MCP SDK not installed')
    def test_real_sdk_stdio_resource_and_click_callback(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        async def run(root,path):
            params=StdioServerParameters(command=sys.executable,args=[str(SCRIPTS/'tv-helper'),'mcp-ui','--session-root',str(root)])
            async with stdio_client(params) as (read,write):
                async with ClientSession(read,write) as client:
                    await client.initialize()
                    listed=await client.list_tools()
                    show=next(t for t in listed.tools if t.name=='tv_ui_show')
                    uri=show.meta['ui']['resourceUri']
                    resource=await client.read_resource(uri)
                    self.assertEqual(resource.contents[0].mimeType,'text/html;profile=mcp-app')
                    self.assertIn('确认选择',resource.contents[0].text)
                    result=await client.call_tool('tv_ui_show',{'session_path':str(path)})
                    self.assertFalse(result.isError,result.content)
                    data=result.structuredContent
                    self.assertEqual(result.meta['ui']['resourceUri'],uri)
                    state_resource=await client.read_resource('tv-state://'+data['session_key'])
                    self.assertEqual(json.loads(state_resource.contents[0].text)['revision'],data['revision'])
                    view=data['presentation']
                    result=await client.call_tool('tv_ui_submit',{'session_key':data['session_key'],'payload':{'question_id':view['question_id'],'presentation_id':view['presentation_id'],'values':['same_wifi']}})
                    self.assertFalse(result.isError,result.content)
                    self.assertEqual(result.structuredContent['presentation']['question_id'],'PRECHECK-ADB-Q1')
                    denied=await client.call_tool('tv_ui_show',{'session_path':str(root.parent/'outside.json')})
                    self.assertTrue(denied.isError)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve(); path=root/'session.json'
            store=SessionStore.create(path,interaction_surface='html',host_platform='claude-desktop')
            store.set_question(build_question('PRECHECK_WIFI',{}))
            asyncio.run(run(root,path))


if __name__=='__main__':unittest.main()
