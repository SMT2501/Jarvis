# Local assistant foundation brief

Date: 10 October 2026
Purpose: Prepare a small offline data foundation for Samkele's income-focused agent without installing software or changing the Virtuo website.
User decisions: Focus on earning income; target South Africa and international clients; current leads are empty; start JARVIS from scratch. Google tools are unavailable in this chat.
Assumptions: Use bundled Python and SQLite. Import only the already reviewed export and profile. Old opportunity mentions are historical, not active leads. No automatic messaging, uploads, background scan or model downloads.
Acceptance criteria:
1. Initialize local storage with the supplied profile sources and no active prospects.
2. Search imported text offline and return the source and excerpt.
3. Store a manually entered prospect with market, evidence and next action; list it without sending anything.
4. Startup and storage must work without additional packages or a network connection.
Limits: This is a CLI foundation, not yet a reasoning agent, browser controller or email integration. No model has been chosen or benchmarked. Website build and launch checklist are not applicable because the repository and website are unchanged.
