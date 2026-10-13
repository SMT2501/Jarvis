# JARVIS agentic CRM product and integration brief

Updated 12 October 2026. User direction: commercially reusable agentic CRM, first proven with Virtuo Designs. An agent team performs bounded work under JARVIS coordination. Personal chat remains one interface, not the whole product.

## Existing source confirmed
Local Git checkout: legacy/virtuo-ai-os. Origin https://github.com/SMT2501/virtuo-ai-os.git; inspected revision 677b7b4. Reuse this existing clone; no second duplicate clone created. Lovable instructions prohibit rewriting published Git history. Nothing was pushed or deployed.
Old app: React 19, TanStack Start/Router, Vite, Supabase; server-side AI provider gateway, Google connection code, CRM pages, org-scoped database access, approvals and specialist definitions. Code presence is not integration verification. Research functions use page fetching and DuckDuckGo Lite parsing. Live provider, Google scopes, RLS, and production behavior have not been verified.
Local app: Python/Tkinter, SQLite, ChatGPT plan sign-in and encrypted Windows credentials. Desktop startup and 09:00 SAST local briefing exist. Specialist workflow is staged and tested with synthetic fixtures; production install status must be recorded separately.

## Architecture direction
Preserve the old application and provider choices. Reuse its UI and domain model. Keep desktop-specific startup, microphone interaction, credential vault and local data access in a separate device runtime. Interfaces connect CRM services to agent tools and provider adapters. Do not expose Windows OAuth tokens to browser code or reuse Sam's credentials for customer accounts.
Tenant isolation: commercial CRM operates in an explicitly selected authenticated workspace. Source org_id fields are a starting point, not proof of isolation. Verify server authorization and database policies for every entity and approval before onboarding another customer. The current SQLite prototype is one user's installation, not a multi-tenant hosted service.
Provider abstraction: customer-owned connections and supported billing routes; local ChatGPT plan usage is not automatically transferable to a paid hosted product. Current official documentation directs paid/remotely hosted applications to its interest flow. Verify eligibility before commercial launch. Reference https://developers.openai.com/siwc/token-sharing-open-source
Data portability: stable, versioned interchange contracts; preserve provenance, unknown values and draft status. No hardcoded Sam profile, prices or credentials in reusable product code. `legacy_bridge.py` maps specialist keys and task states and prepares local lead/task/draft records for review. It does not write remotely or claim approval-table compatibility.

## First proof workflow
1. Give JARVIS a public prospect brief.
2. Research searches and collects source-backed candidates.
3. Lead qualification checks evidence links, duplicates, market and contact route.
4. Sales prepares personalized drafts without inventing price, achievements or contacts.
5. Review evidence and approve exact recipients/messages before delivery.
6. Verified email integration sends only approved messages, with idempotency and delivery/audit records.
7. Track reply, follow-up, opportunity stage and eventually won/lost outcome.
Stages 1–4 are implemented in the staged local workflow. Email sending and old frontend/runtime connection remain unfinished.

## Acceptance and proof criteria
- A bounded batch produces real source-linked candidates or reports that none qualify; unavailable tools never fabricate research.
- Every specialist handoff has a durable input/status/result record, including failures and cancellations.
- A draft cannot be reported as sent; delivery must reference exact human approval and provider evidence.
- Repeated jobs do not duplicate prospects or sends; failed jobs are not counted as success.
- UI capabilities and metrics reflect actual integrations; no undefined/NaN or made-up pipeline values.
- Business proof: initially collect ten genuinely qualified opportunities across local/international markets, review drafts, track outreach/replies and paid conversions. Completion counts measure processing only, not commercial success. No conversions have yet been established.

## Milestones
A. Audit existing source and connect its domain model to the local runtime.
B. Prove Research > Lead > Sales with citations and job history.
C. Connect Gmail reading, approved drafts and follow-up tracking.
D. Use it for Virtuo, measure time saved, quality, replies and paid work.
E. Only then prepare a reusable installer or hosted beta, tenancy tests, account onboarding, provider eligibility, billing, privacy/data lifecycle and release sign-off.

## Current limits
Commercial launch not authorized or ready. No paid plan, cloud deployment, provider migration or remote database change performed. Memory remains personal locally stored context and is excluded from reusable source control. Existing ChatGPT plan-based transport, voice dictation and morning scheduling limitations remain documented in DESKTOP_README.md.
