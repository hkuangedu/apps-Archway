# Archway — Planning Session

**Date:** 2026-05-28
**Participants:** User (fund advisor / project owner), Claude (Opus 4.7 via Claude Code)
**Outcome:** Repo scaffolded, deployed, and a written agent planning + action plan committed.

---

## 1. Repo discovery

**User:** Check my GitHub repo for one called `apps-Archway`.

**Claude:** The repo isn't visible on the public account `hkuangedu`. Could be private, under a different org, or named slightly differently.

**User:** It's private — check for a file called `authentication`. You have access via SSH.

**Claude:** Cloned via SSH. The repo exists but is **completely empty** — no commits, no branches, no files. No `authentication` file because there are no files at all.

---

## 2. Project scoping

**User:** Let's work on this repo. Update the local folder and sync to GitHub.

**Claude:** Asked where the local should live (chose `~/apps-Archway`) and the first task (chose **initialize a project scaffold**).

**User:** Background: building investment tools for the school's student-managed fund — corporate event calendar, analyst rating tracker, and similar workflow tools. **Purpose: students explore using AI to improve workflow**, mirroring what practitioners are doing.

**Claude:** Recommended **Python + Streamlit** — finance/AI workflow demos already live in Python, students can go idea → working tool fast, each tool can be a separate page in a multi-page app. Trade-off: outgrown if going public-facing later.

**User clarified:**
- Hosting: Streamlit Cloud or school infra
- No fundamentals/prices needed — fund has data vendors for that
- AI used to *build* the tools, not at runtime
- Multiple sector teams; each team adds/removes its own tickers

**Decisions locked in:**
- Stack: Python + Streamlit, CSV-backed watchlist (no DB)
- Team model: simple sector picker, no login (v0)
- Data: Finnhub free tier for event calendar + analyst ratings

---

## 3. Scaffold build

Claude wrote 14 files: `app.py`, `pages/1_Watchlist.py`, `pages/2_Event_Calendar.py`, `pages/3_Rating_Tracker.py`, `archway/watchlist.py`, `archway/data/finnhub.py`, seed `data/watchlist.csv`, requirements, gitignore, Streamlit config, README. Committed and pushed.

**User:** Try this API key: `d6sqqkpr01qoqoir50sg...` Don't sync to GitHub.

**Claude:** Tested via env var only — never written to any file. `secrets.toml` confirmed in `.gitignore`. API works: earnings calendar returns next earnings dates (e.g., AAPL 2026-07-29 amc), recommendation endpoint returns aggregated analyst counts. Bumped the calendar default window from 45 → 90 days so first-load shows results. Pushed.

---

## 4. Deployment Q&A

**User:** Why not Netlify?

**Claude:** Netlify only hosts static sites + short serverless functions. Streamlit is a long-running Python server — Netlify can't run it. Right alternatives: **Streamlit Community Cloud** (recommended), Hugging Face Spaces, Render, Railway, Fly.io, or school infra.

**User:** Streamlit free is only public, right?

**Claude:** Mostly — free tier supports unlimited public apps and a small number of private apps (viewers must log in with Google). Repo can be private either way. For Archway v0, public is fine: data isn't sensitive, API key is server-side, easier to share. Go private when sensitive content (notes, positions) is added.

**User:** Set repo to private, Streamlit can't find it.

**Claude:** Need to grant Streamlit access to private repos — either re-authorize from Streamlit Cloud → Linked accounts → GitHub, or in GitHub → Settings → Installed GitHub Apps → Streamlit → Configure → Repository access.

**User:** What's branch, what's main file path?

**Claude:** Branch = `main`, Main file path = `app.py`. The files in `pages/` are auto-discovered by Streamlit.

**User:** Forgot the API key — can I add after deploy?

**Claude:** Yes — app's ⋮ menu → Settings → Secrets → paste `FINNHUB_API_KEY = "..."` → Save. App auto-reboots in ~30s.

---

## 5. Event Calendar redesign + rollback

**User:** Modify the calendar — want Google/Outlook style.

**Claude:** Switched to `streamlit-calendar` (FullCalendar.js wrapper). Month/week/list views, color-coded by sector, click for EPS/revenue details. Pushed.

**User:** Where did you get the rating tracker data?

**Claude:** Finnhub's `/stock/recommendation` endpoint — monthly aggregated counts of Strong Buy / Buy / Hold / Sell / Strong Sell across analysts. Free tier. Caveats: aggregated (no per-analyst detail), updated monthly (not real-time), contributor list not disclosed. Institutional alternatives (Refinitiv I/B/E/S, Bloomberg, S&P Capital IQ) give per-analyst detail.

**User:** Roll back the calendar.

**Claude:** Used `git revert` (non-destructive). Back to the original dataframe view. Streamlit Cloud auto-redeploys.

---

## 6. Agents — concepts

**User:** Can I understand these tools as agents?

**Claude:** **No.** What's built are deterministic scripts/dashboards. An AI agent has: an LLM at the core making decisions, tools it can call autonomously, a plan→act→observe loop, handles ambiguous goals. **AI lives in the building, not the running** today. To turn an Archway tool into an agent: e.g., an Earnings Analyst page where the LLM uses tools (`get_earnings`, `get_filings`, `get_news`) to write a briefing.

**User:** Model? Opus?

**Claude:** Claude Opus 4.7. Best for complex coding/reasoning; Sonnet for cost-balanced runtime agents; Haiku for cheap/fast tasks.

---

## 7. Agent design discussion

**User:** After the calendar, build an agent that fetches earnings data based on calendar events.

**Claude:** Natural next step. The agent's job: each morning, for every ticker reporting today, pull actuals, compare to consensus, scan the press release / news, draft a short briefing. Tools needed: `get_todays_earnings`, `get_actuals`, `get_press_release`, `get_transcript`, `get_news`. Architectural decision worth talking through: live agent (Streamlit page) vs scheduled agent (morning briefing committed to repo / emailed). Recommendation: start live for visibility, graduate to scheduled.

**User:** Should I create governance and verification agents?

**Claude:** For this scale, technically overkill but **a great teaching exercise**. Recommended progression:

| Phase | Agent(s) | Lesson |
|---|---|---|
| v1 | One Briefing Agent + governance stub | Tool use, agent loop, prompting |
| v2 | Add Verification Agent (LLM-as-judge) | Hallucination, self-check, eval patterns |
| v3 | Add Planner Agent | Orchestration, routing |

Verification > governance at this scale because finance has zero tolerance for wrong numbers and the verification check (re-read source, confirm numbers) is concrete.

**User:** What is a governance agent?

**Claude:** Compliance officer analogy:
- **Briefing agent** = research analyst (produces work)
- **Verification agent** = fact-checker (is this *true*?)
- **Governance agent** = compliance officer (is this *allowed*?)

Examples for Archway: enforce watchlist scope, no investment-advice language, mandatory source citation, MNPI scrub, fund-mandate alignment. Implemented as a small LLM that outputs allow/rewrite/block/escalate on each producer output. Overkill at v0 (rules fit in the system prompt), but the pattern is worth a 1-rule stub so students see it.

---

## 8. Reporting workflow — the big multi-agent use case

**User:** Another improvement is reporting — multi-agent system to pull fund data, generate reports per format, with verification + governance.

**Claude:** **This is the right use case for multi-agent**, much better fit than earnings briefing. Sections map cleanly to specialist agents, sections produce in parallel, numbers must tie out (verification non-negotiable), reports go to outside audiences (governance is real).

Proposed architecture:
```
Orchestrator → [Performance, Holdings, Sector, Market agents (parallel)] → Writer → Verification → Governance → Formatter → PPT/Word
```

Phase 2 of Archway.

---

## 9. Big picture — Claude across the stack

**User:** Don't build anything. Big picture — can we build everything using Claude?

**Claude:** Yes — Claude is the intelligence layer in three places:
1. **Claude Code** — builds the system (what we're using)
2. **Claude API** — runs the runtime agents
3. **Claude.ai** — students chat directly for research/ideation

What Claude is *not*: your data feed, file generator, storage, scheduler, or UI. Those are plain engineering (with Claude Code's help).

Honest constraints: cost, latency, hallucination, lock-in, data privacy.

---

## 10. Product map — corrected after web search

**User:** Claude Agent or Claude Cowork?

**Claude (initial):** Didn't recognize "Cowork." Listed Claude.ai / Teams / Code / API / Agent SDK / Managed Agents.

**User:** Web search your own current product.

**Claude (after search) — corrections and new info (May 2026):**

- **Claude Cowork is a real product** — Claude embedded directly in Excel, Word, PowerPoint, MCP-connected to enterprise data. The right answer for daily fund work.
- **Claude Managed Agents** launched April 8, 2026 — hosted REST API; includes lead-agent → specialist-subagent delegation, **built-in rubric grader (the verification agent, productized)**, Dreaming (memory curation), webhooks, self-hosted sandboxes via MCP tunnels.
- **Claude Team plan**: 5–75 seats, $20–25/standard, $100–125/premium (includes Claude Code). Native connectors for Drive, Gmail, Calendar, M365, Slack, GitHub.
- **Agent Skills** — first-class concept; reusable instructions packaged and shareable.

**Updated map:**

| Use case | Product |
|---|---|
| Fund-wide chat, projects, connectors | Claude Team |
| Students inside Excel/Word/PPT | Claude Cowork |
| Building Archway | Claude Code |
| Runtime agents | Claude Managed Agents (preferred) or Agent SDK |
| Pre-built domain agents | Managed Agents library + Skills |

**Roadmap implication:** don't hand-roll governance/verification — Managed Agents' rubric grader **is** the verification agent. Build *on* this, not from scratch.

---

## 11. Decision: Managed Agents as default

**User:** Managed Agents is a good idea — reduces coding/maintenance burden.

**Claude:** Agreed, and the maintenance win is bigger for a student fund specifically because of turnover. The rubric grader alone would be 2–3 months of work to build well — free here. Trade-offs (lock-in, less internal visibility, opaque cost, less plumbing-learning) are acceptable for an educational fund — students focus on high-leverage decisions (what should the agent do? what's the rubric?) instead of weeks of plumbing.

**Approach:**
1. Managed Agents as default for runtime
2. Agent SDK only when needed (rare)
3. Use existing Skills wherever possible
4. Hand-rolled code only for tools (data adapters)

---

## 12. Deliverable

**User:** Give me the agent planning map and action plan as a Word doc, push to GitHub.

**Claude:** Built `docs/Archway_Agent_Planning.docx` (generator: `docs/build_planning_doc.py`). 8 sections: Executive Summary, Current State, Stack Decisions, Agent Planning Map (4 layers), 4-Phase Action Plan, Open Questions, Risks & Mitigations, Educational Outcomes. Pushed.

---

## Open questions remaining

1. Where does fund-level position/return data live (custodian API, vendor, Excel)?
2. Existing report template available to use as the contract?
3. Who pays for Anthropic API usage (school budget vs fund vs advisor account)?
4. Public or private Streamlit deployment once agents handle sensitive content?
5. How are sector commentaries written today (Word, Slack, email)?

## Next session

Pull the actual Managed Agents API docs and sketch the concrete v1 of the Earnings Briefing Agent — tools, system prompt, rubric, Streamlit page integration.
