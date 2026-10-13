"""Small offline section-aware context selector; no external requests."""
import math
import re
from collections import Counter
STOP = set('a an and are as at based be business by can context do facts for from give help i in is it known me my of on or practical separate should some suggest that the their them this three to use we what which will with you your assumptions week'.split())

def words(text):
    return set(re.findall(r'[a-z][a-z0-9]+', text.casefold())) - STOP

def select_context(db, question):
    sections=[]
    for row in db.execute('SELECT path,text FROM sources'):
        # Exported profile has explicit numbered sections; keep headers with bodies.
        for block in re.split(r'(?m)(?=^# \d+\.)',row['text']):
            heading=block.splitlines()[0] if block.splitlines() else ''
            if row['path'].endswith('.json') or not re.match(r'^# \d+\.',heading): continue
            for chunk in block.split('\n\n'):
                chunk=chunk.strip()
                if len(chunk)>80 and not chunk.startswith('#'):
                    sections.append((row['path'],heading,chunk,words(chunk)))
    query=words(question)
    if query & {'income','earn','earning','clients','client','website','websites'}:
        query |= {'sales','acquisition','pricing','services','referrals','outreach','maintenance'}
    counts=Counter(word for _,_,_,tokens in sections for word in tokens)
    ranked=[]
    for path,heading,chunk,tokens in sections:
        overlap=query & tokens
        score=sum(math.log(1+len(sections)/(1+counts[t])) for t in overlap)
        if re.search(r'COMMUNICATE|OPERATE|FINAL INSTRUCTIONS|OPEN THREADS',heading): score*=0.2
        if re.search(r'MAIN COMPANY|SALES|PRIORITIES',heading): score*=1.4
        if score>0: ranked.append((score,path,heading,chunk))
    selected=[]
    headings=Counter()
    for _,path,heading,chunk in sorted(ranked,key=lambda x:x[0],reverse=True):
        if headings[heading]>=2: continue
        excerpt=chunk[:1200]
        if len(chunk)>1200:
            cut=excerpt.rfind('\n')
            if cut>300: excerpt=excerpt[:cut]
            excerpt+='\n[Excerpt shortened]'
        selected.append('Source: '+path+'\n'+heading+'\n'+excerpt)
        headings[heading]+=1
        if len(selected)==4: break
    return '\n\n'.join(selected)
