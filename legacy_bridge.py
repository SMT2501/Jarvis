"""Local interchange adapter for the existing CRM. Never writes to Supabase."""
import uuid

AGENT_KEYS={'core':'jarvis_core','research':'research_agent','lead':'lead_agent','sales':'sales_agent','client':'client_agent','development':'development_agent','finance':'finance_agent','marketing':'marketing_agent','personal':'personal_agent','project':'project_agent'}
TASK_STATUS={'running':'running','completed':'done','failed':'failed','cancelled':'failed','interrupted':'failed'}

def crm_interchange(opportunities,jobs,workspace_id):
    # Caller must select a workspace explicitly; no Sam-specific hardcoded tenant.
    try:workspace=str(uuid.UUID(workspace_id))
    except (ValueError,AttributeError,TypeError):raise ValueError('A valid, explicitly selected workspace UUID is required.') from None
    leads=[];drafts=[]
    for row in opportunities:
        leads.append({'org_id':workspace,'name':row['name'],'company':row['name'],
                      'website':row['website'],'location':'South Africa' if row['market']=='ZA' else 'International; exact location unconfirmed',
                      'service':'Website redesign or maintenance (candidate need)',
                      'status':'new','source':'jarvis_research_pending_review',
                      'notes':row['evidence']+'\nEvidence URL: '+row['evidence_url']+'\nContact page: '+row['contact_url'],
                      'next_action':'Review evidence and draft before outreach'})
        if row.get('draft'):
            drafts.append({'candidate_website':row['website'],'body':row['draft'],'state':'draft_only','sent':False})
    tasks=[]
    for row in jobs:
        if row['agent'] not in AGENT_KEYS or row['status'] not in TASK_STATUS:continue
        tasks.append({'org_id':workspace,'agent_key':AGENT_KEYS[row['agent']],
                      'objective':row['task'],'status':TASK_STATUS[row['status']],
                      'result':{'text':row['result'],'local_status':row['status']}})
    return {'format':'jarvis-crm-interchange','version':1,'workspace_id':workspace,
            'leads_to_review':leads,'agent_tasks':tasks,'drafts_to_map_to_approvals':drafts,
            'remote_write_performed':False,'limitations':'Import API, tenant permission checks and approval schema mapping must be verified before remote import. No private memory or credentials exported.'}
