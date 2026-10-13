import uuid
import unittest
from datetime import datetime, timezone
from pathlib import Path
import desktop_store as store

class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.original=store.DB;store.DB=Path(__file__).parent/('test-'+uuid.uuid4().hex+'.sqlite3')
        self.test_path=store.DB
    def tearDown(self):
        store.DB=self.original;self.test_path.unlink(missing_ok=True)
    def test_briefing_sast_once_and_catchup(self):
        # 06:59 UTC is 08:59 South Africa; 07:00 UTC is 09:00.
        before=datetime(2026,10,13,6,59,tzinfo=timezone.utc)
        after=datetime(2026,10,13,7,0,tzinfo=timezone.utc)
        self.assertFalse(store.due_briefing(before));self.assertTrue(store.due_briefing(after))
        text=store.make_briefing(after);self.assertIn('No active prospects',text)
        store.save_briefing(text,after);self.assertFalse(store.due_briefing(after))
        self.assertTrue(store.due_briefing(datetime(2026,10,14,12,0,tzinfo=timezone.utc)))
    def test_invalid_times(self):
        for t in ['09:00','00:00','23:59']:self.assertTrue(store.valid_time(t))
        for t in ['9:00','24:00','09:60','oops']:self.assertFalse(store.valid_time(t))
    def test_local_tasks_in_briefing(self):
        with store.connect() as db:
            db.execute('INSERT INTO desktop_tasks(title) VALUES (?)',("Prepare client's proposal",))
        self.assertIn("Prepare client's proposal",store.make_briefing())
        with store.connect() as db:db.execute('UPDATE desktop_tasks SET done=1')
        self.assertNotIn("Prepare client's proposal",store.make_briefing())
    def test_failed_replies_excluded(self):
        store.add_message('user','first');store.add_message('assistant','answer')
        store.add_message('user','second');store.add_message('assistant','network failed',False)
        self.assertEqual([r['content'] for r in store.history()],['first','answer'])
    def test_settings_persist(self):
        store.set_setting('morning_time','10:00');self.assertEqual(store.setting('morning_time'),'10:00')

if __name__=='__main__':unittest.main()
