# JARVIS Desktop

Open the Desktop shortcut **JARVIS Local**, or double-click `Start JARVIS.cmd` in this folder. The dark sidebar and console follow Sam's supplied references. Real local counts replace illustrative screenshot figures.

## What works
- Command Center: actual local prospect, task and memory counts.
- Console: streaming ChatGPT conversation, saved local history and model choice. Recent completed exchanges are included when you send the next message; failed replies are excluded.
- Optional profile excerpts: preview and approve before transmission.
- Leads: record qualified prospects with market, evidence and next action.
- Tasks: add actions and mark them complete.
- Memory: shows imported sources; local keyword search is available from the console.
- Morning briefing: local tasks, recorded prospects and a suggested income action, at **09:00 South Africa time**, once daily. It does not fetch email, calendar or fresh prospects.
- Windows startup: launches minimized after signing in, not before login. A missed briefing is delivered on the next check after login/resume while running.
- Closing the window minimizes it. Reopen via the shortcut/taskbar. Use Settings > Quit to stop it. Disable startup or change briefing time in Settings.

## Voice
Talk opens Windows voice typing (Win+H), after a notice and confirmation. This computer's local speech engine failed both .NET and SAPI probes; direct offline dictation is therefore not claimed. Windows voice typing can require internet, a supported language and microphone permission. It may send audio to Microsoft's service. Review the transcript in the message box and press Send yourself.
Read last reply uses Windows speech synthesis. Audio output and microphone transcription require a manual device test and have not been verified. JARVIS never listens continuously.

## Limits and data
No Gmail connection, live prospect research, specialist agent workforce, background code execution or computer-control tools have been added. AI requires internet and uses the existing ChatGPT plan. No large package or model download was needed. This desktop version uses Tkinter and bundled Python rather than Electron to keep installation small.

Chat history, tasks, sources and briefings are ordinary local SQLite records, not encrypted. ChatGPT credentials remain separately Windows-DPAPI encrypted. Recent conversation is sent to OpenAI when you submit a chat message. Source excerpts are opt-in. Never share `.auth` or the personal context database.

## Architecture
`desktop.py`: native UI, worker/event queue, single-instance loopback activation and 30-second briefing checks. `desktop_store.py`: SQLite desktop tables and SAST scheduler. `startup.py`: reversible HKCU Run entry `JarvisLocal`. `chatgpt_connection.py`: shared CLI/desktop OAuth and Responses transport. Desktop shortcut targets bundled pythonw and this project. Existing CLI and memory database are preserved. Settings and briefings are local app behavior, not Codex scheduled tasks.

Tests and limits are recorded in DESKTOP_VERIFICATION.md. This is an evolving local app, not a standalone packaged installer. It currently depends on the bundled runtime remaining at its existing location.

Agentic CRM upgrade: Agents page and Research > Lead > Sales workflow are installed. See AGENT_TEAM_README.md and AGENTIC_CRM_BRIEF.md; older capability descriptions above predate this upgrade. Existing old CRM source is in legacy/virtuo-ai-os. Frontend/runtime and remote import remain pending.
