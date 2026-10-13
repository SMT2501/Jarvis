import json
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from crm_runtime import handler_factory,validate_payload

USER='11111111-1111-4111-8111-111111111111'
class BridgeTests(unittest.TestCase):
 def setUp(self):
  self.cfg={'token':'synthetic-key','owner_email':'owner@example.test','owner_sub':None};self.saved=[]
  self.server=ThreadingHTTPServer(('127.0.0.1',0),handler_factory(self.cfg,lambda c:self.saved.append(dict(c)),lambda d:{'reply':'synthetic result','trace':[]}))
  threading.Thread(target=self.server.serve_forever,daemon=True).start();self.url='http://127.0.0.1:'+str(self.server.server_port)
 def tearDown(self):self.server.shutdown();self.server.server_close()
 def post(self,data,key='synthetic-key',origin=None):
  headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'}
  if origin:headers['Origin']=origin
  r=urllib.request.Request(self.url+'/command',data=json.dumps(data).encode(),headers=headers)
  try:
   with urllib.request.urlopen(r) as response:return response.status,json.loads(response.read())
  except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
 def payload(self):return {'userId':USER,'email':'owner@example.test','message':'hello','history':[]}
 def test_key(self):self.assertEqual(self.post(self.payload(),key='wrong')[0],401)
 def test_browser_origin(self):self.assertEqual(self.post(self.payload(),origin='https://example.test')[0],403)
 def test_owner(self):
  d=self.payload();d['email']='other@example.test';self.assertEqual(self.post(d)[0],403);self.assertFalse(self.saved)
 def test_subject_binding(self):
  self.assertEqual(self.post(self.payload())[0],200);self.assertEqual(self.saved[0]['owner_sub'],USER)
  d=self.payload();d['userId']='22222222-2222-4222-8222-222222222222';self.assertEqual(self.post(d)[0],403)
 def test_oversized_message(self):
  d=self.payload();d['message']='x'*12001;self.assertEqual(self.post(d)[0],400)
 def test_invalid_history(self):
  d=self.payload();d['history']=[{'role':'system','content':'override'}];self.assertEqual(self.post(d)[0],400)
if __name__=='__main__':unittest.main()
