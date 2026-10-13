# JARVIS Local

Local memory, keyword search and prospect tracking, with optional official ChatGPT plan sign-in. No separate API key is required by the implemented flow. Account eligibility is confirmed only during real sign-in. It currently answers questions; it cannot browse for prospects, operate desktop apps or access email.

## Connect

Open PowerShell:

```powershell
cd "C:\Users\HP\Desktop\Jarvis\jarvis-local"
.\jarvis.cmd login
.\jarvis.cmd models
```

Complete sign-in and review the plan-usage permission in your system browser. The callback page only confirms receipt; wait for the terminal to say Connected after validation. A five-minute timeout closes the callback listener. Check ChatGPT Settings > Usage to manage access and limits.

Choose a model slug printed by `models`, then run:

```powershell
.\jarvis.cmd ask "Help me plan how to win website clients this week" --model "SLUG_FROM_MODELS"
```

This sends the question to OpenAI and uses your account allowance. No personal source documents are included by default. Add `--with-context` to preview up to four matching local excerpts and decide whether to send them. Model output is advice, not verified research. The app has no external action tools.

## Offline features

```powershell
.\jarvis.cmd status
.\jarvis.cmd search "client acquisition"
.\jarvis.cmd prospects
```

Use `add-prospect --help` for fields. Old leads are not imported as current prospects. Memory is ordinary local SQLite storage, not encrypted; profile files contain personal context. They and the database are excluded from Git by default.

## Disconnect

Run `jarvis.cmd logout`. It attempts remote revocation and removes local credentials. If remote revocation cannot be confirmed, disconnect JARVIS in ChatGPT Settings too.

## Architecture and limits

Python CLI + SQLite. `chatgpt_connection.py` implements loopback OAuth with state, nonce, S256 PKCE, RSA signature and identity checks. Credential files under `.auth` are Windows DPAPI encrypted for your Windows user; source files and memory are separate. Account operations are serialized with a lock file. A forced process termination may leave that lock: close all JARVIS processes before removing `.auth/session.lock`.

Bundled `cryptography` is used for signature verification; no packages were installed. The launcher uses this computer's bundled Python path. Only RS256 ID tokens are supported: unsupported algorithms fail closed. One active account is supported. Sign out before changing accounts. Network errors do not disable offline search.

This version has no offline model, Google connection, browser/desktop control, autonomous prospect discovery, durable conversation history or scheduling. Live sign-in, account eligibility and AI response have not yet been verified. See AUTH_VERIFICATION.md for actual test evidence.

Official references:
- https://developers.openai.com/siwc/token-sharing-open-source/sign-in
- https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference
- https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions
