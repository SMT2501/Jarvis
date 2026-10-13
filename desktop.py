"""JARVIS native desktop; all Tk calls stay on its UI thread."""
import argparse
import json
import os
import queue
import socket
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText
import chatgpt_connection as ai
import desktop_store as store
import startup
import agent_team
from retrieval import select_context

BASE=Path(__file__).resolve().parent
CREATE_NO_WINDOW=getattr(subprocess,'CREATE_NO_WINDOW',0)
PS=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'

class App:
    def __init__(self,root,minimized=False):
        agent_team.recover()
        self.agent_cancel=threading.Event()
        self.root=root; self.events=queue.Queue(); self.busy=False; self.last_reply='';self.closed=False
        self.root.title('JARVIS • Virtuo workspace');self.root.geometry('1180x760');self.root.minsize(960,620)
        self.root.configure(bg='#0c0f12')
        style=ttk.Style();style.theme_use('clam')
        style.configure('TButton',padding=(12,8),background='#182126',foreground='#e8edf2',borderwidth=0);style.map('TButton',background=[('active','#26353d')]);style.configure('TNotebook.Tab',padding=(16,8))
        style.configure('TFrame',background='#0c0f12');style.configure('TCheckbutton',background='#0c0f12',foreground='#d4dde5');style.configure('TEntry',fieldbackground='#151a20',foreground='#e8edf2');style.configure('TCombobox',fieldbackground='#151a20',foreground='#e8edf2');style.map('TCombobox',fieldbackground=[('readonly','#151a20')],foreground=[('readonly','#e8edf2')])
        style.layout('TNotebook.Tab',[])
        style.configure('TNotebook',background='#0c0f12',borderwidth=0,relief='flat')
        style.layout('TNotebook',[('Notebook.client',{'sticky':'nswe'})])
        self.root.option_add('*Text.background','#10161b')
        self.root.option_add('*Text.foreground','#d4dde5')
        self.root.option_add('*Text.insertBackground','#46c8df')
        self.root.option_add('*Text.selectBackground','#224352')
        self.root.option_add('*Text.selectForeground','#ffffff')
        self.root.option_add('*Text.highlightThickness',0)
        self.root.option_add('*Toplevel.background','#0c0f12')
        style.configure('Treeview',background='#10161b',fieldbackground='#10161b',foreground='#d4dde5',rowheight=32);style.configure('Treeview.Heading',background='#182126',foreground='#d4dde5');style.map('Treeview',background=[('selected','#224352')])
        style.configure('TLabel',background='#0c0f12',foreground='#d4dde5',font=('Segoe UI',10))
        self.sidebar=tk.Frame(root,bg='#080b0e',width=204);self.sidebar.pack(side='left',fill='y');self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar,text='●  J A R V I S',bg='#080b0e',fg='#e4f6ff',font=('Consolas',15,'bold'),anchor='w').pack(fill='x',padx=18,pady=(24,4))
        tk.Label(self.sidebar,text='Personal AI workspace',bg='#080b0e',fg='#8097a8',font=('Segoe UI',9),anchor='w').pack(fill='x',padx=18,pady=(0,24))
        shell=ttk.Frame(root);shell.pack(side='left',fill='both',expand=True)
        header=ttk.Frame(shell,padding=14);header.pack(fill='x')
        ttk.Label(header,text='JARVIS',font=('Segoe UI',22,'bold')).pack(side='left')
        self.state=tk.StringVar(value='Checking connection…');ttk.Label(header,textvariable=self.state).pack(side='left',padx=20)
        ttk.Button(header,text='Connect ChatGPT',command=self.login).pack(side='right')
        self.tabs=ttk.Notebook(shell);self.tabs.pack(fill='both',expand=True,padx=14,pady=8)
        self.agents=ttk.Frame(self.tabs,padding=18);self.home=ttk.Frame(self.tabs,padding=18);self.leads=ttk.Frame(self.tabs,padding=18);self.memory=ttk.Frame(self.tabs,padding=18);self.activity=ttk.Frame(self.tabs,padding=18);self.chat=ttk.Frame(self.tabs,padding=12);self.tasks=ttk.Frame(self.tabs,padding=12);self.brief=ttk.Frame(self.tabs,padding=12);self.settings=ttk.Frame(self.tabs,padding=12)
        for frame,name in [(self.home,'Command Center'),(self.chat,'Console'),(self.leads,'Leads'),(self.agents,'Agents'),(self.tasks,'Tasks'),(self.memory,'Memory'),(self.brief,'Morning briefing'),(self.activity,'Activity'),(self.settings,'Settings')]:
            self.tabs.add(frame,text=name)
            tk.Button(self.sidebar,text=name,anchor='w',bg='#080b0e',fg='#d4dde5',activebackground='#1c252b',activeforeground='#46c8df',relief='flat',font=('Segoe UI',11),padx=20,pady=12,command=lambda f=frame:self.navigate(f)).pack(fill='x')
        tk.Label(self.sidebar,text='LOCAL WORKSPACE\nVirtuo Designs\nSouth Africa + international',justify='left',bg='#080b0e',fg='#8097a8',font=('Segoe UI',9)).pack(side='bottom',pady=22)
        self.build_dashboard()
        self.build_leads()
        self.build_memory()
        self.build_agents()
        self.activity_text=ScrolledText(self.activity,wrap='word',bg='#10161b',fg='#d4dde5',font=('Segoe UI',11));self.activity_text.pack(fill='both',expand=True)
        self.activity_text.insert('end','Activity is recorded locally. ChatGPT requests use your plan.\n')
        self.activity_text.configure(state='disabled')
        toolbar=ttk.Frame(self.chat);toolbar.pack(fill='x')
        ttk.Label(toolbar,text='Model').pack(side='left')
        self.model=tk.StringVar(value=store.setting('model','gpt-6.1-sol'))
        self.picker=ttk.Combobox(toolbar,textvariable=self.model,state='readonly',width=24);self.picker.pack(side='left',padx=8)
        self.picker.bind('<<ComboboxSelected>>',lambda e:store.set_setting('model',self.model.get()))
        ttk.Button(toolbar,text='Refresh models',command=self.load_models).pack(side='left')
        self.use_context=tk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar,text='Include profile excerpts (preview first)',variable=self.use_context).pack(side='right')
        self.transcript=ScrolledText(self.chat,wrap='word',font=('Segoe UI',11),bg='#0c0f12',fg='#d4dde5',insertbackground='#46c8df',relief='flat',padx=14,pady=14,state='disabled');# transcript packed after composer to preserve send controls
        self.transcript.tag_config('user',foreground='#46c8df',font=('Segoe UI',11,'bold'))
        self.transcript.tag_config('assistant',foreground='#61d69b',font=('Segoe UI',11,'bold'))
        for row in store.messages():self.write_message(row['role'],row['text']+(' [Incomplete]' if not row['complete'] else ''))
        if not store.messages():self.write_message('assistant','Hi Sam. Ask me about your work, or add tasks for your morning briefing. AI chat uses your ChatGPT plan online. Local tasks and search work offline.')
        self.input=tk.Text(self.chat,height=3,wrap='word',font=('Segoe UI',11),bg='#141a1f',fg='#edf4f7',insertbackground='#46c8df',relief='flat',padx=10,pady=10);self.input.pack(side='bottom',fill='x')
        self.input.bind('<Control-Return>',lambda e:self.send())
        controls=ttk.Frame(self.chat);controls.pack(side='bottom',fill='x',pady=8)
        self.send_button=ttk.Button(controls,text='Send • Ctrl+Enter',command=self.send);self.send_button.pack(side='right')
        self.mic_button=ttk.Button(controls,text='Talk • Windows dictation',command=self.listen);self.mic_button.pack(side='left')
        ttk.Button(controls,text='Read last reply',command=self.speak).pack(side='left',padx=6)
        ttk.Button(controls,text='Search local files',command=self.search).pack(side='left')
        self.transcript.pack(fill='both',expand=True,pady=12)
        ttk.Label(self.tasks,text='Keep your next actions here. They appear in the daily briefing.').pack(anchor='w')
        self.task_list=tk.Listbox(self.tasks,font=('Segoe UI',12),bg='#10161b',fg='#d4dde5',selectbackground='#224352',relief='flat',height=18);self.task_list.pack(fill='both',expand=True,pady=12)
        actions=ttk.Frame(self.tasks);actions.pack(fill='x')
        ttk.Button(actions,text='Add task',command=self.add_task).pack(side='left')
        ttk.Button(actions,text='Mark selected done',command=self.complete_task).pack(side='left',padx=6)
        self.refresh_tasks()
        self.brief_text=ScrolledText(self.brief,wrap='word',font=('Segoe UI',12),bg='#10161b',fg='#d4dde5',state='disabled');self.brief_text.pack(fill='both',expand=True)
        ttk.Button(self.brief,text='Refresh local briefing',command=self.show_briefing).pack(anchor='e',pady=8)
        self.start_var=tk.BooleanVar(value=startup.enabled())
        ttk.Checkbutton(self.settings,text='Start JARVIS when I sign in to Windows',variable=self.start_var,command=self.toggle_startup).pack(anchor='w',pady=10)
        self.morning_var=tk.BooleanVar(value=store.setting('morning_enabled',True))
        ttk.Checkbutton(self.settings,text='Show my daily morning briefing',variable=self.morning_var,command=lambda:store.set_setting('morning_enabled',self.morning_var.get())).pack(anchor='w',pady=10)
        time_row=ttk.Frame(self.settings);time_row.pack(anchor='w',pady=10)
        ttk.Label(time_row,text='Briefing time (South Africa, HH:MM)').pack(side='left')
        self.morning_time=tk.StringVar(value=store.setting('morning_time','09:00'))
        ttk.Entry(time_row,textvariable=self.morning_time,width=8).pack(side='left',padx=8)
        ttk.Button(time_row,text='Save time',command=self.save_time).pack(side='left')
        ttk.Label(self.settings,text='Closing the window minimizes JARVIS so briefings can continue.\nUse Quit to stop it. Briefings arrive at the next check after login or sleep.\nTalk opens Windows dictation on demand; review text before sending.\nChat history is stored locally and recent successful exchanges go to OpenAI\nwhen you send another message. Profile excerpts require separate approval.\nEmail/calendar are not connected. Public research is available from Agents when permitted by your account.',justify='left').pack(anchor='w',pady=15)
        ttk.Button(self.settings,text='Disconnect ChatGPT',command=self.logout).pack(anchor='w',pady=8)
        ttk.Button(self.settings,text='Quit JARVIS',command=self.quit).pack(anchor='w',pady=8)
        self.footer=tk.StringVar(value='Ready • AI online; local memory offline')
        ttk.Label(shell,textvariable=self.footer,padding=10).pack(fill='x')
        root.protocol('WM_DELETE_WINDOW',root.iconify)
        root.after(100,self.poll);root.after(1200,self.check_briefing)
        self.load_models()
        if minimized:root.after(50,root.iconify)

    def navigate(self,frame):
        self.tabs.select(frame)
        if frame==self.home:self.update_dashboard()
        if frame==self.leads:self.update_leads()
        if frame==self.agents:self.refresh_agents()

    def log(self,text):
        if hasattr(self,'activity_text'):
            self.activity_text.configure(state='normal');self.activity_text.insert('end',text+'\n');self.activity_text.configure(state='disabled')

    def build_dashboard(self):
        ttk.Label(self.home,text='Welcome back, Sam',font=('Segoe UI',22,'bold')).pack(anchor='w')
        ttk.Label(self.home,text='Your workspace for turning opportunities into paid work.').pack(anchor='w',pady=(4,22))
        cards=ttk.Frame(self.home);cards.pack(fill='x')
        self.metrics={}
        for title in ['NEW PROSPECTS','OPEN TASKS','LOCAL SOURCES']:
            card=tk.Frame(cards,bg='#12181d',highlightbackground='#283039',highlightthickness=1);card.pack(side='left',fill='x',expand=True,padx=(0,10))
            tk.Label(card,text=title,bg='#12181d',fg='#8199a8',font=('Consolas',9),anchor='w').pack(fill='x',padx=16,pady=(16,6))
            value=tk.StringVar(value='0');self.metrics[title]=value
            tk.Label(card,textvariable=value,bg='#12181d',fg='#42c4df',font=('Consolas',25),anchor='w').pack(fill='x',padx=16,pady=(0,16))
        ttk.Label(self.home,text='TODAY’S FOCUS',font=('Consolas',11)).pack(anchor='w',pady=(28,10))
        self.priorities=tk.StringVar()
        ttk.Label(self.home,textvariable=self.priorities,wraplength=730,justify='left',font=('Segoe UI',12)).pack(anchor='w')
        buttons=ttk.Frame(self.home);buttons.pack(anchor='w',pady=24)
        ttk.Button(buttons,text='Open console',command=lambda:self.navigate(self.chat)).pack(side='left')
        ttk.Button(buttons,text='Morning briefing',command=self.show_briefing).pack(side='left',padx=8)
        ttk.Label(self.home,text='CONNECTIONS',font=('Consolas',11)).pack(anchor='w',pady=(10,10))
        ttk.Label(self.home,text='ChatGPT: signed-in account is checked when used.\nMemory and tasks: available locally.\nGmail and calendar: not connected. Public prospect research: available from Agents.\nAgent team: Core → Research → Lead → Sales. Other specialist integrations are pending.',justify='left').pack(anchor='w')
        self.update_dashboard()

    def update_dashboard(self):
        with store.connect() as db:
            count=db.execute('SELECT count(*) FROM desktop_tasks WHERE done=0').fetchone()[0]
            self.metrics['OPEN TASKS'].set(str(count))
            try:
                self.metrics['NEW PROSPECTS'].set(str(db.execute("SELECT count(*) FROM prospects WHERE status='uncontacted'").fetchone()[0]))
                self.metrics['LOCAL SOURCES'].set(str(db.execute('SELECT count(*) FROM sources').fetchone()[0]))
            except Exception:pass
            tasks=[r[0] for r in db.execute('SELECT title FROM desktop_tasks WHERE done=0 ORDER BY id LIMIT 4')]
        self.priorities.set('\n'.join('• '+s for s in tasks) if tasks else 'No tasks recorded yet. Start with one clear offer, then qualify one local and one international prospect.')

    def build_leads(self):
        ttk.Label(self.leads,text='Income pipeline',font=('Segoe UI',20,'bold')).pack(anchor='w')
        ttk.Label(self.leads,text='Only prospects you record appear here. Historical leads are not imported as active.').pack(anchor='w',pady=8)
        self.lead_list=ttk.Treeview(self.leads,columns=('name','market','status','next'),show='headings')
        for col,title in [('name','Business'),('market','Market'),('status','Status'),('next','Next action')]:self.lead_list.heading(col,text=title);self.lead_list.column(col,width=140 if col!='next' else 320)
        self.lead_list.pack(fill='both',expand=True,pady=12)
        ttk.Button(self.leads,text='Add prospect',command=self.add_lead).pack(anchor='e')
        self.update_leads()

    def update_leads(self):
        self.lead_list.delete(*self.lead_list.get_children())
        import jarvis
        with jarvis.connect() as db:
            for r in db.execute('SELECT * FROM prospects ORDER BY id'):self.lead_list.insert('','end',values=(r['name'],r['market'],r['status'],r['next_action']))

    def add_lead(self):
        dialog=tk.Toplevel(self.root);dialog.title('Record a qualified prospect');dialog.geometry('490x400');dialog.transient(self.root)
        fields={}
        for label in ['Business name','Market (ZA or international)','Evidence of need','Next action']:
            ttk.Label(dialog,text=label).pack(anchor='w',padx=18,pady=(12,2));v=tk.StringVar();ttk.Entry(dialog,textvariable=v,width=60).pack(padx=18,fill='x');fields[label]=v
        def save():
            name,market,evidence,action=[v.get().strip() for v in fields.values()]
            if not all([name,market,evidence,action]) or market not in ['ZA','international']:
                messagebox.showinfo('Details','Complete every field; market must be ZA or international.',parent=dialog);return
            import jarvis
            with jarvis.connect() as db:db.execute('INSERT INTO prospects(name,market,evidence,next_action) VALUES (?,?,?,?)',(name,market,evidence,action))
            dialog.destroy();self.update_leads();self.update_dashboard();self.log('Prospect saved locally; no outreach sent.')
        ttk.Button(dialog,text='Save locally',command=save).pack(pady=20)

    def build_memory(self):
        ttk.Label(self.memory,text='Your local memory',font=('Segoe UI',20,'bold')).pack(anchor='w')
        ttk.Label(self.memory,text='Source text stays on this device until you approve excerpts for a chat request.').pack(anchor='w',pady=8)
        view=ScrolledText(self.memory,wrap='word',bg='#10161b',fg='#d4dde5',font=('Segoe UI',11));view.pack(fill='both',expand=True)
        import jarvis
        with jarvis.connect() as db:
            for row in db.execute('SELECT path,text FROM sources'):view.insert('end',row['path']+'\n'+str(len(row['text']))+' characters • historical context\n\n')
        view.configure(state='disabled')

    def build_agents(self):
        ttk.Label(self.agents,text='Your agent team',font=('Segoe UI',20,'bold')).pack(anchor='w')
        ttk.Label(self.agents,text='JARVIS coordinates specialist handoffs. Research → qualification → outreach drafts.').pack(anchor='w',pady=6)
        self.agent_rows=ttk.Treeview(self.agents,columns=('role','state','counts'),show='headings',height=10)
        for key,title,width in [('role','Specialist',230),('state','Capability / current state',330),('counts','Recent completed / failed',180)]:self.agent_rows.heading(key,text=title);self.agent_rows.column(key,width=width)
        self.agent_rows.pack(fill='x',pady=8)
        row=ttk.Frame(self.agents);row.pack(fill='x')
        ttk.Button(row,text='Run income workflow',command=self.start_agents).pack(side='left')
        ttk.Button(row,text='Cancel current job',command=self.agent_cancel.set).pack(side='left',padx=8)
        ttk.Button(row,text='Refresh status',command=self.refresh_agents).pack(side='right')
        self.agent_reports=ttk.Treeview(self.agents,columns=('id','business','market','draft'),show='headings',height=5)
        for key,title in [('id','ID'),('business','Researched business'),('market','Market'),('draft','Draft status')]:self.agent_reports.heading(key,text=title);self.agent_reports.column(key,width=80 if key=='id' else 200)
        self.agent_reports.pack(fill='both',expand=True,pady=10)
        ttk.Button(self.agents,text='Review selected evidence and draft',command=self.view_report).pack(anchor='e')
        self.refresh_agents()

    def refresh_agents(self):
        jobs=agent_team.summary()
        self.agent_rows.delete(*self.agent_rows.get_children())
        for key,name,description,enabled in agent_team.ROLES:
            own=[j for j in jobs if j['agent']==key]
            state='Not connected' if not enabled else ('Running' if any(j['status']=='running' for j in own) else 'Ready')
            counts=str(sum(j['status']=='completed' for j in own))+' / '+str(sum(j['status']=='failed' for j in own))
            self.agent_rows.insert('','end',values=(name,state,counts))
        self.agent_reports.delete(*self.agent_reports.get_children())
        for r in agent_team.opportunities():self.agent_reports.insert('','end',iid=str(r['id']),values=(r['id'],r['name'],r['market'],'Ready for review' if r['draft'] else 'Not drafted'))

    def start_agents(self,task=None):
        if self.busy:messagebox.showinfo('Busy','Wait for the current request to finish.');return
        task=task or simpledialog.askstring('Income workflow','Public research brief (do not include private documents):',initialvalue='Find up to four small businesses, two in South Africa and two internationally, with specific evidence of a website redesign or maintenance need. Use public sources and actual contact pages.',parent=self.root)
        if not task:return
        if not messagebox.askyesno('Run specialist workflow','This uses up to two AI requests and web search on your ChatGPT account. The public brief and agent handoffs are sent to OpenAI. Private profile documents are not included. Candidates and drafts are saved locally; nothing is sent to prospects. Continue?',parent=self.root):return
        self.input.delete('1.0','end')
        self.write_message('assistant','Dispatching Research → Lead Qualification → Sales Drafting. Progress will appear here. Email sending is not connected; nothing will be sent.')
        self.agent_cancel.clear();self.busy=True;self.footer.set('JARVIS is coordinating the team…');model=self.model.get()
        self.worker(lambda:agent_team.run_income(model,task,notify=lambda text:self.events.put(('agent_progress',text)),cancel=self.agent_cancel),'agents')

    def view_report(self):
        selection=self.agent_reports.selection()
        if not selection:return
        record=next((r for r in agent_team.opportunities() if str(r['id'])==selection[0]),None)
        if not record:return
        view=tk.Toplevel(self.root);view.title('Evidence and outreach draft • '+record['name']);view.geometry('800x610')
        text=ScrolledText(view,wrap='word',font=('Segoe UI',11));text.pack(fill='both',expand=True,padx=12,pady=12)
        text.insert('end',record['name']+'\nMarket: '+record['market']+'\nWebsite: '+record['website']+'\n\nObserved evidence (review before use):\n'+record['evidence']+'\nSource: '+record['evidence_url']+'\nContact page: '+record['contact_url']+'\nSource-coverage score: '+str(record['score'])+' (not buying probability)\n\nDraft — not sent:\n'+(record['draft'] or 'No completed draft available.'))
        text.configure(state='disabled')
        ttk.Button(view,text='Close',command=view.destroy).pack(pady=8)

    def write_message(self,role,text):
        self.transcript.configure(state='normal');self.transcript.insert('end',role.upper()+'\n',role)
        self.transcript.insert('end',text+'\n\n');self.transcript.configure(state='disabled');self.transcript.see('end')

    def worker(self,fn,kind):
        def run():
            try:self.events.put((kind,fn()))
            except Exception as e:self.events.put(('error',(kind,str(e) if isinstance(e,RuntimeError) else 'Operation failed ('+type(e).__name__+').')))
        threading.Thread(target=run,daemon=True).start()

    def load_models(self):
        self.worker(lambda:ai.models(),'models')

    def login(self):
        if self.busy:return
        self.busy=True;self.footer.set('Complete ChatGPT sign-in in your browser…')
        self.worker(ai.login,'login')

    def logout(self):
        if self.busy:return
        if not messagebox.askyesno('Disconnect','Disconnect this app from your ChatGPT account?',parent=self.root):return
        self.busy=True;self.worker(ai.logout,'logout')

    def preview(self,text):
        dialog=tk.Toplevel(self.root);dialog.title('Review profile excerpts sent to OpenAI');dialog.geometry('760x530');dialog.transient(self.root)
        view=ScrolledText(dialog,wrap='word',font=('Segoe UI',10));view.pack(fill='both',expand=True,padx=12,pady=12);view.insert('end',text);view.configure(state='disabled')
        approved=[False]
        def yes():approved[0]=True;dialog.destroy()
        ttk.Button(dialog,text='Approve excerpts and send',command=yes).pack(side='right',padx=12,pady=12)
        ttk.Button(dialog,text='Cancel',command=dialog.destroy).pack(side='right',padx=12,pady=12)
        dialog.grab_set();self.root.wait_window(dialog);return approved[0]

    def send(self):
        if self.busy:return
        question=self.input.get('1.0','end').strip()
        if not question:return
        from intent_router import intent, research_brief, CAPABILITIES
        route=intent(question)
        if route=='capabilities':
            store.add_message('user',question);self.write_message('user',question)
            store.add_message('assistant',CAPABILITIES);self.write_message('assistant',CAPABILITIES)
            self.input.delete('1.0','end');return
        if route=='income':
            self.start_agents(research_brief(question));return
        if len(question)>12000:messagebox.showinfo('Message too long','Keep this message under 12,000 characters.');return
        context=''
        if self.use_context.get():
            import jarvis
            with jarvis.connect() as db:context=select_context(db,question)
            if context and not self.preview(context):return
        previous=store.history()
        store.add_message('user',question);self.write_message('user',question)
        self.input.delete('1.0','end');self.busy=True;self.send_button.configure(state='disabled');self.footer.set('JARVIS is thinking…')
        self.partial='';self.transcript.configure(state='normal');self.transcript.insert('end','JARVIS\n','assistant');self.transcript.configure(state='disabled')
        selected_model=self.model.get()
        self.worker(lambda:ai.ask(question,selected_model,context,on_delta=lambda s:self.events.put(('delta',s)),history=previous,context_approved=True),'reply')

    def poll(self):
        try:
            while True:
                kind,data=self.events.get_nowait()
                if kind=='agent_progress':self.footer.set(data);self.log(data);self.write_message('assistant',data);self.refresh_agents()
                elif kind=='agents':self.finish('Workflow finished. Open Agents to review results.');self.refresh_agents();self.update_leads();self.update_dashboard()
                elif kind=='show':self.root.deiconify();self.root.lift()
                elif kind=='delta':
                    self.partial+=data;self.transcript.configure(state='normal');self.transcript.insert('end',data);self.transcript.configure(state='disabled');self.transcript.see('end')
                elif kind=='reply':
                    store.add_message('assistant',data);self.last_reply=data;self.log('AI reply completed');self.transcript.configure(state='normal');self.transcript.insert('end','\n\n');self.transcript.configure(state='disabled');self.finish('Ready')
                elif kind=='models':
                    slugs=[m['slug'] for m in data];self.picker.configure(values=slugs)
                    if slugs and self.model.get() not in slugs:self.model.set(slugs[0])
                    self.state.set('ChatGPT connected' if slugs else 'No eligible models')
                elif kind=='login':self.finish('Connected');self.load_models()
                elif kind=='logout':self.state.set('Not connected');self.finish('Disconnected. Check ChatGPT Settings if remote revocation was not confirmed.')
                elif kind=='speech':
                    self.mic_button.configure(state='normal')
                    if data.get('error'):self.footer.set(data['error'])
                    else:self.input.insert('end',data.get('text',''));self.footer.set('Review what I heard, then press Send.')
                elif kind=='spoken':self.footer.set('Read-aloud finished.')
                elif kind=='error':
                    operation,data=data
                    if operation=='reply' and self.busy and hasattr(self,'partial'):
                        store.add_message('assistant',self.partial+'\n[Failed: '+data+']',False)
                        self.transcript.configure(state='normal');self.transcript.insert('end','\n[Failed: '+data+']\n\n');self.transcript.configure(state='disabled')
                    self.mic_button.configure(state='normal')
                    if operation=='models':self.state.set('AI unavailable • local tools ready');self.footer.set(data)
                    elif operation in ['reply','login','logout','agents']:self.finish(data)
                    else:self.footer.set(data)
        except queue.Empty:pass
        if not self.closed:self.root.after(80,self.poll)

    def finish(self,text):
        self.busy=False;self.send_button.configure(state='normal');self.footer.set(text)

    def listen(self):
        # Local speech-engine probes failed on this device. Use the Windows dictation UI.
        if not messagebox.askyesno('Windows voice typing',
            'JARVIS could not load a local Windows speech recognizer.\n\nUse Windows voice typing instead? It may use Microsoft’s online speech service and microphone permission. Recognized text stays in the message box until you press Send.',parent=self.root):return
        self.input.focus_set()
        def launch_dictation():
            import ctypes
            user=ctypes.windll.user32
            user.keybd_event(0x5B,0,0,0)
            user.keybd_event(0x48,0,0,0)
            user.keybd_event(0x48,0,2,0)
            user.keybd_event(0x5B,0,2,0)
            self.footer.set('Windows dictation opened. Review recognized text before Send. If unavailable, press Win+H or use typed chat.')
        self.root.after(150,launch_dictation)

    def speak(self):
        if not self.last_reply:self.footer.set('No completed reply to read yet.');return
        text=self.last_reply[:6000]
        def read():
            p=subprocess.run([str(PS),'-NoProfile','-File',str(BASE/'speak.ps1')],input=text,capture_output=True,timeout=150,encoding='utf-8',creationflags=CREATE_NO_WINDOW)
            if p.returncode:raise RuntimeError('Windows read-aloud unavailable.')
        self.worker(read,'spoken')

    def search(self):
        query=self.input.get('1.0','end').strip()
        if not query:self.footer.set('Type search words in the message box first.');return
        import jarvis
        with jarvis.connect() as db:result=select_context(db,query)
        self.write_message('assistant','Local search (no network):\n'+(result or 'No matches.'))

    def refresh_tasks(self):
        with store.connect() as db:self.task_rows=[dict(r) for r in db.execute('SELECT * FROM desktop_tasks WHERE done=0 ORDER BY id')]
        self.task_list.delete(0,'end')
        for row in self.task_rows:self.task_list.insert('end',row['title'])

    def add_task(self):
        text=simpledialog.askstring('Add task','What is the next action?',parent=self.root)
        if text and text.strip():
            with store.connect() as db:db.execute('INSERT INTO desktop_tasks(title) VALUES (?)',(text.strip(),))
            self.refresh_tasks()

    def complete_task(self):
        selection=self.task_list.curselection()
        if selection:
            with store.connect() as db:db.execute('UPDATE desktop_tasks SET done=1 WHERE id=?',(self.task_rows[selection[0]]['id'],))
            self.refresh_tasks()

    def show_briefing(self):
        text=store.make_briefing();self.brief_text.configure(state='normal');self.brief_text.delete('1.0','end');self.brief_text.insert('end',text);self.brief_text.configure(state='disabled');self.tabs.select(self.brief)
        return text

    def check_briefing(self):
        if self.morning_var.get() and store.due_briefing():
            text=self.show_briefing();store.save_briefing(text);self.root.deiconify();self.root.lift();self.root.bell();self.footer.set('Your morning briefing is ready.')
        if not self.closed:self.root.after(30000,self.check_briefing)

    def save_time(self):
        value=self.morning_time.get().strip()
        if not store.valid_time(value):messagebox.showinfo('Time','Use HH:MM, for example 08:00.');return
        store.set_setting('morning_time',value);self.footer.set('Morning briefing time saved (South Africa).')

    def toggle_startup(self):
        try:startup.set_enabled(self.start_var.get());self.footer.set('Windows startup setting saved.')
        except Exception:self.start_var.set(startup.enabled());messagebox.showerror('Startup','Could not update Windows startup registration.')

    def quit(self):
        if self.busy and not messagebox.askyesno('Quit','A request is running. Quit anyway?',parent=self.root):return
        self.closed=True;self.root.destroy()


def main():
    args=argparse.ArgumentParser();args.add_argument('--minimized',action='store_true');args.add_argument('--smoke-test',action='store_true');opts=args.parse_args()
    # A loopback guard ensures startup and desktop shortcut do not launch duplicate schedulers.
    guard=socket.socket();guard.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
    try:guard.bind(('127.0.0.1',0 if opts.smoke_test else 47831))
    except OSError:
        try:
            with socket.create_connection(('127.0.0.1',47831),timeout=1) as client:client.sendall(b'show')
        except OSError:pass
        guard.close();return
    guard.listen(3)
    root=tk.Tk()
    if opts.smoke_test:
        # UI smoke test avoids real account requests and speech/microphone access.
        ai.models=lambda:[]
    app=App(root,opts.minimized)
    def activation_listener():
        while not app.closed:
            try:
                client,_=guard.accept()
                with client:
                    client.settimeout(1)
                    if client.recv(16)==b'show':app.events.put(('show',None))
            except OSError:break
    threading.Thread(target=activation_listener,daemon=True).start()
    if opts.smoke_test:
        app.add_task=lambda:None
        def check_layout():
            app.tabs.select(app.chat)
            root.update_idletasks()
            try:
                assert ttk.Style().lookup('TLabel','foreground')=='#d4dde5'
                assert int(ttk.Style().lookup('TNotebook','borderwidth'))==0
                assert len(app.tabs.tabs())==9
                assert app.input.winfo_width()>400
                assert app.sidebar.winfo_width()==204
                print('Desktop smoke test passed: nine pages and usable console layout.')
            finally:root.destroy()
        root.after(500,check_layout)
    try:root.mainloop()
    finally:guard.close()

if __name__=='__main__':
    try:main()
    except Exception as e:
        try:
            root=tk.Tk();root.withdraw();messagebox.showerror('JARVIS startup error','Could not start ('+type(e).__name__+'). Open Desktop README for troubleshooting.');root.destroy()
        except Exception:pass
        raise
