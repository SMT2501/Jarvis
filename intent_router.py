"""Conservative routing of current user requests, not imported conversation text."""
import re

DEFAULT_BRIEF='Find up to four evidence-linked website redesign or maintenance opportunities, in South Africa and internationally. Prioritize active buyers where available. Use public sources and actual business contact routes. Prepare drafts only; no sending.'

def intent(text):
    q=' '.join(text.casefold().split())
    if q.startswith('/income '):return 'income'
    # Questions about abilities are explanations, never commands.
    if re.search(r'can you (?:talk|speak|communicate|connect).*agents|what (?:can|do).*agents|are .*agents connected',q):return 'capabilities'
    if re.search(r"\b(?:do not|don't|dont|never|stop|cancel)\b",q):return 'chat'
    if re.search(r'\b(?:find|get|research|source|look for|identify)\b.{0,65}\b(?:clients|prospects|leads|buyers|website opportunities)\b',q):return 'income'
    if re.search(r'\b(?:give|assign|delegate|dispatch)\b.{0,45}\b(?:work|tasks|prospecting)\b.{0,35}\bagents\b',q):return 'income'
    return 'chat'

def research_brief(text):
    if text.casefold().startswith('/income '):return text[8:].strip()
    # Original instruction stays local; forwarding only preparation avoids telling a specialist to send.
    q=re.sub(r'\b(?:and\s+)?send\b.*', '', text,flags=re.I).strip()
    return DEFAULT_BRIEF+'\nAdditional public research direction: '+q

CAPABILITIES='Yes. This app can dispatch the Research → Lead Qualification → Sales Drafting workflow. Ask me to find clients or assign prospecting to the agents. Research uses public web sources, Lead checks evidence and duplicates, and Sales prepares drafts. Email sending is not connected, so no proposal can be sent yet. Other specialist roles are not connected.'
