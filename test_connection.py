import contextlib
import io
import json
import time
import unittest
from unittest.mock import patch
import chatgpt_connection as ai
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

class ConnectionTests(unittest.TestCase):
    def test_callbacks(self):
        self.assertEqual(ai.callback_values('state=ok&code=test&client_id=oaiapp_test','ok','dynamic_agent_client')['client_id'],'oaiapp_test')
        for query, client in [('state=bad&code=test&client_id=oaiapp_test','dynamic_agent_client'),('state=ok&code=test','dynamic_agent_client'),('state=ok&code=test&client_id=other','oaiapp_test'),('state=ok&state=ok&code=test','oaiapp_test')]:
            with self.assertRaises(ValueError): ai.callback_values(query,'ok',client)
        self.assertTrue(ai.callback_values('state=ok&error=access_denied','ok','dynamic_agent_client')['denied'])

    def test_verified_identity(self):
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        numbers=key.public_key().public_numbers()
        keys=[{'kid':'test','kty':'RSA','n':ai.b64(numbers.n.to_bytes(256,'big')),'e':ai.b64(numbers.e.to_bytes(3,'big'))}]
        def token(claims):
            h=ai.b64(json.dumps({'alg':'RS256','kid':'test'}).encode())
            p=ai.b64(json.dumps(claims).encode())
            sig=key.sign((h+'.'+p).encode(),padding.PKCS1v15(),hashes.SHA256())
            return h+'.'+p+'.'+ai.b64(sig)
        claims={'iss':ai.ISSUER,'aud':'oaiapp_test','exp':time.time()+60,'sub':'synthetic','nonce':'nonce'}
        self.assertEqual(ai.validate_identity(token(claims),'oaiapp_test','nonce',keys)['sub'],'synthetic')
        for changes in [{'nonce':'wrong'},{'iss':'https://evil.invalid'},{'aud':'other'},{'exp':0}]:
            with self.assertRaises(RuntimeError): ai.validate_identity(token(dict(claims,**changes)),'oaiapp_test','nonce',keys)
        t=token(claims);h,p,s=t.split('.')
        with self.assertRaises(RuntimeError): ai.validate_identity(h+'.'+ai.b64(b'{}')+'.'+s,'oaiapp_test','nonce',keys)

    def test_windows_encryption(self):
        raw=b'synthetic test credential'
        encrypted=ai.protect(raw)
        self.assertNotEqual(raw,encrypted)
        self.assertEqual(ai.protect(encrypted,True),raw)

    def test_permission_required(self):
        with self.assertRaises(RuntimeError): ai.token_record({'access_token':'synthetic','token_type':'Bearer','scope':'openid'},'test','test')
        record=ai.token_record({'access_token':'synthetic','token_type':'Bearer','scope':'chatgpt.tokens.use.direct','expires_in':3600},'test','test')
        self.assertIn('chatgpt.tokens.use.direct',record['scopes'])

    def test_context_cancel(self):
        with patch.object(ai,'models',return_value=[{'slug':'test'}]), patch('builtins.input',return_value='n'),patch.object(ai.urllib.request,'urlopen') as network,contextlib.redirect_stdout(io.StringIO()):
            ai.ask('question','test','private test excerpt')
            network.assert_not_called()

    def test_stream_completion(self):
        events=[b'data: {"type":"response.output_text.delta","delta":"hello"}\n',b'data: {"type":"response.completed"}\n']
        class Stream:
            def __enter__(self): return iter(events)
            def __exit__(self,*args): pass
        with patch.object(ai,'models',return_value=[{'slug':'test'}]),patch.object(ai,'access_token',return_value='synthetic'),patch.object(ai.urllib.request,'urlopen',return_value=Stream()) as network,contextlib.redirect_stdout(io.StringIO()) as out:
            ai.ask('question','test')
            request=network.call_args.args[0]
            body=json.loads(request.data)
            self.assertFalse(body['store']); self.assertTrue(body['stream'])
            self.assertIsInstance(body['input'], list)
            self.assertNotIn('max_output_tokens', body)
            self.assertEqual(out.getvalue(),'hello\n')
        events.pop()
        with patch.object(ai,'models',return_value=[{'slug':'test'}]),patch.object(ai,'access_token',return_value='synthetic'),patch.object(ai.urllib.request,'urlopen',return_value=Stream()),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError): ai.ask('question','test')

if __name__=='__main__': unittest.main()
