# React CRM primary interface

The primary launcher will open the actual cloned React/TanStack CRM at http://127.0.0.1:5178. It is a local development runtime, not a production installer or deployment. Existing Supabase architecture and remote data are preserved. Browser sign-in to the CRM may be needed; it is separate from ChatGPT login.

Private server-side settings (Supabase service role, Lovable AI and Google connector keys) are not present in the clone's environment. Their dependent functions are unverified/unavailable locally until configured via the supported service setup. Do not paste credentials into chat or put them in browser code. The hosted Gmail connection has not been migrated.

Python desktop prototype remains available through Start JARVIS Prototype.cmd. Its memory, ChatGPT connection and jobs have not been moved into the cloned CRM. Unifying these is the next integration step, not completed by changing the launcher.

Local server binds only to loopback. Runtime PID and startup logs are in .react-runtime (excluded from source control). The local server must be running to open the interface. This launcher currently depends on installed Node and Python paths and is not a distributable commercial package.

Primary shortcut has been switched and the login route verified. JarvisCRM startup opens the React interface; prior prototype morning runner remains separate. First boot can take several minutes. Interactive sign-in/dashboard verification is still required. See legacy/virtuo-ai-os/docs/LOCAL_INTERFACE_SESSION.md.
