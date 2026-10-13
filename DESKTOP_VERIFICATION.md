# Desktop verification

12 October 2026. Five desktop logic tests passed: SAST time conversion and 09:00 threshold, once-per-day/catch-up scheduling, time validation, task completion reflected in briefing, failed exchanges excluded from model history, and persistent settings (some grouped in one test). Six existing authentication/transport tests passed after adding streaming callbacks and history support. Tkinter initialized and all eight pages constructed; smoke check selected Console and confirmed a usable message-box width and sidebar width. Initial hidden-tab layout assertion was corrected to select the Console before measurement. No full visual screenshot inspection was available.

Voice: direct Windows System.Speech InstalledRecognizers failed (NullReference) both restricted and elevated; SAPI probe returned 0x80045039. Implemented Windows voice typing fallback with runtime consent. Microphone transcription and read-aloud playback remain unverified. No microphone was activated during probes.

Morning behavior tested with synthetic dates, not an overnight run or reboot. Startup registration and shortcut must be verified during installation. No live AI request with private profile or chat history was run in these tests. Prior CLI minimal live inference passed before this change; desktop live chat needs user test.

Installation verified: original credentials and memory preserved; HKCU Run startup entry matches expected app command; 09:00 and daily briefings saved; Desktop JARVIS Local shortcut created.
