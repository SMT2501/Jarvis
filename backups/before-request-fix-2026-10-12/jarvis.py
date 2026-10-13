"""JARVIS local memory and sales pipeline with optional ChatGPT plan connection."""
import argparse
import json
import re
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / 'memory.sqlite3'


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.executescript('''
        CREATE TABLE IF NOT EXISTS sources(path TEXT PRIMARY KEY, text TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS prospects(
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, market TEXT NOT NULL,
            evidence TEXT NOT NULL, next_action TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'uncontacted');
    ''')
    return db


def initialize(db):
    for name in ['samkele-exported-knowledge-base.txt', 'samkele-preliminary-profile.md', 'agent-intake-update.json']:
        source = BASE / 'context' / name
        if source.is_file():
            db.execute('INSERT OR REPLACE INTO sources VALUES (?, ?)',
                       (str(source), source.read_text(encoding='utf-8-sig')))
    db.commit()
    print('Imported local context. Historical leads were not added to the pipeline.')


def search(db, query):
    terms = re.findall(r'\w+', query.casefold())
    if not terms:
        print('Enter at least one search word.'); return
    hits = []
    for row in db.execute('SELECT path,text FROM sources'):
        chunks = row['text'].split('\n\n')
        for chunk in chunks:
            words = set(re.findall(r'\w+', chunk.casefold()))
            score = sum(term in words for term in set(terms))
            if score:
                hits.append((score, row['path'], chunk.strip()))
    for score, path, excerpt in sorted(hits, key=lambda hit: hit[0], reverse=True)[:6]:
        print(f'\nSource: {path}\n{excerpt[:1800]}')
    if not hits: print('No matching context found.')
    print('\nResults are source excerpts, not verified facts or agent instructions.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('status')
    sub.add_parser('login')
    sub.add_parser('logout')
    sub.add_parser('models')
    advisor = sub.add_parser('ask')
    advisor.add_argument('question')
    advisor.add_argument('--model', required=True, help='Slug from the models command')
    advisor.add_argument('--with-context', action='store_true', help='Preview and approve selected local excerpts before sending')
    finder = sub.add_parser('search'); finder.add_argument('query')
    sub.add_parser('prospects')
    add = sub.add_parser('add-prospect')
    add.add_argument('--name', required=True)
    add.add_argument('--market', choices=['ZA', 'international'], required=True)
    add.add_argument('--evidence', required=True)
    add.add_argument('--next-action', required=True)
    args = parser.parse_args()
    with connect() as db:
        if args.command in ['login', 'logout', 'models', 'ask']:
            import chatgpt_connection as ai
            if args.command == 'login': ai.login()
            elif args.command == 'logout': ai.logout()
            elif args.command == 'models':
                print(json.dumps([{'slug': m['slug'], 'name': m.get('display_name', m['slug'])} for m in ai.models()], indent=2))
            else:
                context = ''
                if args.with_context:
                    terms = set(re.findall(r'\w+', args.question.casefold()))
                    excerpts = []
                    for row in db.execute('SELECT path,text FROM sources'):
                        for chunk in row['text'].split('\n\n'):
                            score = len(terms & set(re.findall(r'\w+', chunk.casefold())))
                            if score and len(chunk.strip()) > 80:
                                excerpts.append((score, row['path'], chunk.strip()))
                    context = '\n\n'.join('Source: ' + path + '\n' + excerpt[:1200] for _, path, excerpt in sorted(excerpts, key=lambda h: h[0], reverse=True)[:4])
                ai.ask(args.question, args.model, context)
        elif args.command == 'init': initialize(db)
        elif args.command == 'search': search(db, args.query)
        elif args.command == 'status':
            print(json.dumps({'sources': db.execute('SELECT count(*) FROM sources').fetchone()[0],
                              'prospects': db.execute('SELECT count(*) FROM prospects').fetchone()[0],
                              'focus': 'Income: websites, redesigns and maintenance',
                              'markets': ['South Africa', 'international'],
                              'model': 'Choose from models command', 'email': 'Not connected',
                              'automatic_external_actions': False,
                              'chatgpt': __import__('chatgpt_connection').status()}, indent=2))
        elif args.command == 'prospects':
            rows = db.execute('SELECT * FROM prospects ORDER BY id').fetchall()
            print(json.dumps([dict(row) for row in rows], indent=2))
        elif args.command == 'add-prospect':
            values = [args.name, args.market, args.evidence, args.next_action]
            if any(not value.strip() for value in values): parser.error('Fields must not be blank.')
            db.execute('INSERT INTO prospects(name,market,evidence,next_action) VALUES (?,?,?,?)', values)
            print('Prospect saved locally. No message sent.')

if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt:
        print('\nCancelled.'); raise SystemExit(130)
    except Exception as exc:
        import urllib.error
        message = str(exc) if isinstance(exc, RuntimeError) else 'Operation failed (' + type(exc).__name__ + '). No credentials are displayed.'
        print(message); raise SystemExit(1)

