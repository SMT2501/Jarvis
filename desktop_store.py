import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE/'memory.sqlite3'
SAST = timezone(timedelta(hours=2))

class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try: return super().__exit__(*args)
        finally: self.close()

def connect():
    db=sqlite3.connect(DB,factory=ClosingConnection); db.row_factory=sqlite3.Row
    db.executescript('''
    CREATE TABLE IF NOT EXISTS desktop_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS desktop_messages(id INTEGER PRIMARY KEY,role TEXT NOT NULL,text TEXT NOT NULL,complete INTEGER NOT NULL DEFAULT 1,created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS desktop_tasks(id INTEGER PRIMARY KEY,title TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS desktop_briefings(day TEXT PRIMARY KEY,text TEXT NOT NULL);
    ''')
    return db

def setting(key,default=None):
    with connect() as db:
        r=db.execute('SELECT value FROM desktop_settings WHERE key=?',(key,)).fetchone()
        return json.loads(r[0]) if r else default

def set_setting(key,value):
    with connect() as db: db.execute('INSERT OR REPLACE INTO desktop_settings VALUES (?,?)',(key,json.dumps(value)))

def valid_time(value):
    try:
        h,m=value.split(':')
        return len(h)==len(m)==2 and 0<=int(h)<24 and 0<=int(m)<60
    except (ValueError,AttributeError): return False

def due_briefing(now=None):
    now=(now or datetime.now(SAST)).astimezone(SAST)
    hour=setting('morning_time','09:00')
    if not valid_time(hour): hour='09:00'
    if now.strftime('%H:%M')<hour: return False
    with connect() as db:
        return db.execute('SELECT 1 FROM desktop_briefings WHERE day=?',(now.date().isoformat(),)).fetchone() is None

def make_briefing(now=None):
    now=(now or datetime.now(SAST)).astimezone(SAST)
    with connect() as db:
        tasks=db.execute('SELECT title FROM desktop_tasks WHERE done=0 ORDER BY id LIMIT 6').fetchall()
        try: leads=db.execute("SELECT name,next_action FROM prospects WHERE status NOT IN ('closed','rejected','inactive') ORDER BY id LIMIT 5").fetchall()
        except sqlite3.OperationalError: leads=[]
    lines=[f"Good morning, Sam — {now.strftime('%A, %d %B %Y')}", '', 'Your focus: earn income through Virtuo websites, redesigns and maintenance.', '', 'Your tasks:']
    lines += ['• '+r['title'] for r in tasks] or ['No tasks recorded yet. Add today’s most important commitment.']
    lines+=['','Income pipeline:']
    lines += ['• '+r['name']+' — '+r['next_action'] for r in leads] or ['No active prospects recorded. Start by qualifying one local and one international prospect.']
    lines+=['','Suggested next action: choose one clear offer and a relevant portfolio example, then prepare personalized outreach.','', 'This is a local briefing. Email, calendar and live opportunity research are not connected.']
    return '\n'.join(lines)

def save_briefing(text,now=None):
    day=(now or datetime.now(SAST)).astimezone(SAST).date().isoformat()
    with connect() as db: db.execute('INSERT OR IGNORE INTO desktop_briefings VALUES (?,?)',(day,text))

def messages(limit=60):
    with connect() as db:
        return [dict(r) for r in db.execute('SELECT * FROM (SELECT * FROM desktop_messages ORDER BY id DESC LIMIT ?) ORDER BY id',(limit,))]

def history():
    rows=messages()
    # A failed exchange is retained for display but omitted from model history.
    result=[]
    for i,row in enumerate(rows):
        if row['role']=='assistant' and row['complete'] and i>0 and rows[i-1]['role']=='user':
            result.extend([{'role':'user','content':rows[i-1]['text']},{'role':'assistant','content':row['text']}])
    return result[-12:]

def add_message(role,text,complete=True):
    with connect() as db: db.execute('INSERT INTO desktop_messages(role,text,complete,created) VALUES (?,?,?,?)',(role,text,int(complete),datetime.now(SAST).isoformat()))
