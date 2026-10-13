import json
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
import desktop_store as store
import agent_team as team

SAMPLE={'name':'Synthetic Studio','market':'ZA','website':'https://example.org','evidence':'Synthetic website maintenance issue for testing only','evidence_url':'https://example.org/contact','contact_url':'https://example.org/contact'}
REPORT={'text':json.dumps({'candidates':[SAMPLE]}),'sources':['https://example.org/contact'],'web_used':True}

class TeamTests(unittest.TestCase):
    def setUp(self):
        self.old=store.DB;store.DB=Path(__file__).parent/('test-'+uuid.uuid4().hex+'.sqlite3');self.path=store.DB
        with store.connect() as db:db.execute('CREATE TABLE prospects(id INTEGER PRIMARY KEY,name TEXT,market TEXT,evidence TEXT,next_action TEXT,status TEXT)')
        team.initialize()
    def tearDown(self):store.DB=self.old;self.path.unlink(missing_ok=True)
    def test_evidence_required(self):
        self.assertEqual(len(team.qualify(REPORT)),1)
        self.assertEqual(team.qualify(dict(REPORT,sources=[])),[])
        bad=dict(SAMPLE,contact_url='https://other.example/contact')
        self.assertEqual(team.qualify(dict(REPORT,text=json.dumps({'candidates':[bad]}))),[])
    def test_complete_handoff_and_duplicates(self):
        responses=[REPORT,{'text':json.dumps({'drafts':[{'id':1,'text':'Synthetic test outreach. Not sent.'}]}),'sources':[]}]
        with patch.object(team.ai,'agent_request',side_effect=responses) as calls:team.run_income('test-model','Synthetic test brief')
        self.assertEqual(calls.call_count,2)
        rows=team.opportunities();self.assertEqual(len(rows),1);self.assertTrue(rows[0]['draft'])
        with store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM prospects').fetchone()[0],1)
        with patch.object(team.ai,'agent_request',return_value=REPORT) as calls:team.run_income('test-model','Synthetic duplicate brief')
        self.assertEqual(calls.call_count,1);self.assertEqual(len(team.opportunities()),1)
        self.assertTrue(all(j['status']=='completed' for j in team.summary()))
    def test_failure_persisted(self):
        with patch.object(team.ai,'agent_request',side_effect=RuntimeError('network unavailable')):
            with self.assertRaises(RuntimeError):team.run_income('test','test')
        self.assertEqual(len(team.opportunities()),0)
        self.assertTrue(all(j['status']=='failed' for j in team.summary()))
    def test_cancel_stops_handoffs(self):
        stop=threading.Event();stop.set()
        with patch.object(team.ai,'agent_request',side_effect=RuntimeError('cancelled')):
            with self.assertRaises(RuntimeError):team.run_income('test','test',cancel=stop)
        self.assertTrue(all(j['status']=='cancelled' for j in team.summary()))
    def test_interrupted_recovery(self):
        key=team.job('research','test');team.recover()
        self.assertEqual(team.summary()[0]['status'],'interrupted')
    def test_wrong_draft_ids_rejected(self):
        self.assertEqual(team.save_drafts({'text':'{"drafts":[{"id":99,"text":"test"}]}'},{1}),0)
    def test_invalid_json_rejected(self):
        with self.assertRaises(RuntimeError):team.object_json('not JSON')

if __name__=='__main__':unittest.main()
