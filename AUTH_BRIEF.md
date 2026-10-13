# ChatGPT connection brief

12 October 2026. Add official ChatGPT plan sign-in to the existing local CLI. No API key, model downloads, website edits, Gmail access, or autonomous computer actions.
Acceptance: (1) browser OAuth with state, nonce and PKCE and validated ID token; (2) Windows DPAPI encryption for credentials with atomic saves and serialized access; (3) account model catalog and bounded streaming requests, with store=false; (4) offline search survives authentication/network failures; (5) imported context is previewed and approved before transmission.
Assumptions: single account per installation; RS256 tokens supported, other algorithms fail closed; cryptography comes from bundled runtime. User completes browser sign-in/consent. Live eligibility, authentication and inference remain unverified until that step. No deployment; website checklist not applicable.
