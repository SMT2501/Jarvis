"""Private loopback bridge for the authenticated local CRM server."""
import argparse
import hmac
import io
import json
import secrets
import threading
import uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
import chatgpt_connection as ai
import desktop_store as store
import agent_team
from intent_router import intent,research_brief,CAPABILITIES

PORT=5179
CONFIG='crm_bridge.bin'
LOCK=threading.Lock()


def configuration():
    result=ai.load(CONFIG,True)
    if not result:raise RuntimeError('Local CRM bridge is not configured.')
    return result


def configure(owner_email):
    if '@' not in owner_email:raise ValueError('Owner email required.')
    current=ai.load(CONFIG,True)
    if current:
        if current['owner_email'].casefold()!=owner_email.casefold():raise RuntimeError('Device already configured for another owner.')
        return current
    result={'token':secrets.token_urlsafe(48),'owner_email':owner_email.casefold(),'owner_sub':None}
    ai.save(CONFIG,result,True)
    return result


def validate_payload(data):
    if not isinstance(data,dict):raise ValueError('JSON object required.')
    for field in ['userId','email','message']:
        if not isinstance(data.get(field),str) or not data[field].strip():raise ValueError('Missing request fields.')
    uuid.UUID(data['userId'])
    if len(data['message'])>12000:raise ValueError('Message exceeds 12,000 characters.')
    history=data.get('history',[])
    if not isinstance(history,list) or len(history)>40:raise ValueError('Invalid history.')
    for turn in history:
        if not isinstance(turn,dict) or turn.get('role') not in ['user','assistant'] or not isinstance(turn.get('content'),str) or len(turn['content'])>12000:raise ValueError('Invalid history turn.')
    return data


def authorize_owner(config,data,persist):
    if not hmac.compare_digest(config['owner_email'],data['email'].casefold()):raise PermissionError('This device runtime is reserved for its configured CRM owner.')
    if config.get('owner_sub') and config['owner_sub']!=data['userId']:raise PermissionError('This CRM account is not paired with the device.')
    if not config.get('owner_sub'):
        config['owner_sub']=data['userId'];persist(config)


def execute(data):
    message=data['message'];route=intent(message)
    if route=='capabilities':return {'reply':CAPABILITIES,'trace':[]}
    model=store.setting('model','gpt-6.1-sol')
    if route=='income':
        trace=[]
        def notify(text):
            role=next((key for prefix,key in [('Research Agent','research_agent'),('Lead Agent','lead_agent'),('Sales Agent','sales_agent')] if text.startswith(prefix)),'jarvis_core')
            trace.append({'agent':role,'tool':'runtime.income_workflow','label':text})
        previous={r['id'] for r in agent_team.opportunities()}
        agent_team.run_income(model,research_brief(message),notify=notify)
        records=[r for r in agent_team.opportunities() if r['id'] not in previous]
        reply=(trace[-1]['label'] if trace else 'Workflow completed.')+'\n\nCandidates and drafts are saved locally, not yet imported into the cloud CRM. Nothing sent.'
        if records:
            for r in records[:4]:reply+='\n\n'+r['name']+' — '+r['market']+'\nEvidence: '+r['evidence']+'\nSource: '+r['evidence_url']+'\nContact: '+r['contact_url']+'\nDraft: '+(r['draft'] or 'Not completed')
        return {'reply':reply,'trace':trace}
    # Entire profile is not added. History contains only supplied conversation turns.
    parts=[]
    answer=ai.ask(message,model,on_delta=parts.append,history=data.get('history',[]),context_approved=True)
    return {'reply':answer,'trace':[{'agent':'jarvis_core','tool':'runtime.chatgpt','label':'Answered using the device ChatGPT account'}]}


def handler_factory(config,persist=lambda value:ai.save(CONFIG,value,True),executor=execute):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def respond(self,status,payload):
            raw=json.dumps(payload).encode();self.send_response(status)
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
        def permitted(self):
            if self.headers.get('Origin'):
                self.respond(403,{'error':'Browser access to runtime is prohibited.'});return False
            expected='Bearer '+config['token']
            if not hmac.compare_digest(self.headers.get('Authorization',''),expected):
                self.respond(401,{'error':'Unauthorized runtime request.'});return False
            host=self.headers.get('Host','')
            if host!=f'127.0.0.1:{self.server.server_port}':
                self.respond(403,{'error':'Invalid runtime host.'});return False
            return True
        def do_GET(self):
            if not self.permitted():return
            if self.path!='/health':self.respond(404,{'error':'Not found'});return
            self.respond(200,{'service':'jarvis-local-runtime','chatgpt':ai.status(),'paired':bool(config.get('owner_sub'))})
        def do_POST(self):
            if not self.permitted():return
            if self.path!='/command':self.respond(404,{'error':'Not found'});return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if self.headers.get('Transfer-Encoding') or not 0<length<=200000:raise ValueError('Invalid body length.')
                self.connection.settimeout(30)
                data=validate_payload(json.loads(self.rfile.read(length)))
            except (ValueError,TimeoutError):self.respond(400,{'error':'Invalid or oversized runtime request.'});return
            if not LOCK.acquire(blocking=False):self.respond(409,{'error':'Local runtime is busy; wait and retry.'});return
            try:
                authorize_owner(config,data,persist)
                self.respond(200,executor(data))
            except PermissionError as e:self.respond(403,{'error':str(e)})
            except RuntimeError as e:self.respond(502,{'error':str(e)})
            except Exception:self.respond(500,{'error':'Local runtime failed. No success recorded.'})
            finally:LOCK.release()
    return Handler


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--configure-owner');args=parser.parse_args()
    if args.configure_owner:
        configure(args.configure_owner);print('Device CRM owner configured. Credentials remain protected.');return
    config=configuration();server=ThreadingHTTPServer(('127.0.0.1',PORT),handler_factory(config))
    server.daemon_threads=True
    print('Local CRM runtime listening on loopback.',flush=True)
    server.serve_forever()

if __name__=='__main__':main()
