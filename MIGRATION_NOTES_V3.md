# Pastify v3 — Premium Overhaul: Migration Notes

## Run it
```bash
pip install -r requirements.txt
streamlit run Home.py
```
Bring your own `past_papers.db` and `output_questions/` folder as before.
A new local file, `progress.db`, will be created automatically next to
`past_papers.db` the first time anyone answers a question — that's where
streaks, badges, and analytics history live (see the "Profiles" note below).

## What changed, file by file

| File | Change |
|---|---|
| `config.py` | Added `PROGRESS_DB_PATH`, `ensure_indexes()` (real SQLite indexes on every column the filter cascade queries — this was a full-table-scan before), `CART_KEYS`, and gamification thresholds. |
| `database.py` | Calls `ensure_indexes()` once per connection. New `search_topics()` for the dynamic keyword search bar. |
| `progress.py` **(new)** | Local SQLite-backed attempt history: `log_attempt`, `get_history`, `compute_streak`, `compute_badges`, `get_topic_accuracy`, `get_daily_activity`. |
| `profile.py` **(new)** | Lightweight, non-auth "who's using this" identity via `st.dialog`, shown once per session. **Read the caveat below before deploying this multi-user.** |
| `analytics.py` **(new)** | Plotly chart builders: accuracy heatmap, time-per-question, activity trend, accuracy donut. |
| `theme.py` / `styles.css` | Full visual overhaul — proper color system (primary/accent/success/warning/danger), gradient hero, card hover states, badge shelf styling. Still the same per-session CSS-variable override approach (no global config.toml writes). |
| `components.py` | Filter sidebar rebuilt around `st.popover` + `st.tabs` instead of five stacked expanders, plus a keyword search box up top. New cart functions (`add_paper_to_cart`, `render_cart_summary`) and gamification widgets (`render_badge_shelf`, `render_streak_indicator`). |
| `feedback.py` | Answer buttons now run inside `st.fragment` — a click reruns only that small component, not the whole page (previously every click re-executed the full script, including the PDF render pipeline and sidebar filter cascade). Every answer is logged to `progress.db` with time taken. |
| `Home.py` | Added the "My Progress" page to `st.navigation`; calls the one-time profile dialog before routing. |
| `pages_src/landing.py` | Gradient hero, tile-based navigation, live streak + badge preview. |
| `pages_src/browse.py` | Added a "🛒 Add to cart" button per question, feeding the Worksheet Builder. |
| `pages_src/worksheet.py` | Rebuilt around a persistent cart: filter → "Add all matching to cart" → review → `st.dialog` confirmation → generate. No more accidentally merging the wrong 80 PDFs from one misclick. |
| `pages_src/quiz.py` / `timed_test.py` | Use the fragment-based answer component; log every attempt for analytics; Timed Test's end screen is now a real dashboard (accuracy heatmap, donut, badges) instead of two bare metrics. |
| `pages_src/my_progress.py` **(new)** | Dedicated analytics dashboard: accuracy by topic, pacing, 30-day activity trend, badge shelf. |

## A real bug caught and fixed mid-build (worth knowing about)

The quiz/timed-test linked-list nodes store `(pdf_path, topic, correct_answer)`.
`feedback.py`'s progress-logging code initially read `node.data[0]` as the
"question number" — that's actually the PDF path. Every logged attempt
would have recorded a nonsense value in `progress.db`, silently corrupting
the whole analytics feature. Caught via an end-to-end test (see below) and
fixed by threading the real `Question_Number` through as a 4th tuple
element in `quiz.py`, `timed_test.py`, and `feedback.py`.

## A second bug caught and fixed mid-build: duplicate dialog crash

The first draft had **every page** call the dialog-capable `profile.get_profile()`
in its own `render()`, in addition to `Home.py` calling it once before
routing. `st.dialog`-decorated functions can't safely be invoked twice in
the same script run — this would have thrown a `DuplicateWidgetID` error
for every new user, the very first time they opened the app. Fixed by
splitting into `get_profile()` (dialog-capable, called exactly once, only
from `Home.py`) and `current_profile()` (a plain, dialog-free session-state
read, used everywhere else). Verified with a test that asserts the dialog
function is invoked exactly once across a simulated multi-page run.

## Testing performed in this sandbox (no live Streamlit available — see caveat)

I don't have network access or a Streamlit/Plotly install in this
environment, so nothing here was clicked through in a real browser. What
I *could* and did verify, with real SQLite and stubbed-but-behaviorally-
accurate `streamlit` module standing in for the parts that need a live app:

- `database.py` against your actual `past_papers.db`: indexes created,
  keyword search returns correct results, quiz-ready subject detection
  matches earlier findings (Accounting/Economics/Physics).
- `progress.py` end-to-end: a simulated 3-day streak computed correctly,
  badge thresholds fire correctly, per-topic accuracy aggregates correctly.
- `feedback.py`'s fragment-based answer flow end-to-end, including
  confirming the question-number bug fix actually logs the right value
  and the correct/wrong counters update.
- The answer-lock behavior (can't re-answer a question once submitted).
- The cart's dedup logic (adding the same question twice is a no-op).
- The profile dialog is triggered exactly once across a simulated
  multi-page navigation, confirming the duplicate-dialog fix.

**Not verified**: actual rendering/interaction of `st.popover`, `st.tabs`,
`st.segmented_control`, `st.fragment(run_every=...)`, and Plotly charts in
a real browser. Please click through each page — especially the Advanced
Filters popover and a full Timed Test run — before relying on this in
front of students.

## The profile/progress caveat, stated plainly

Pastify has no real authentication. "Profile" is a self-chosen display
name typed into a dialog on first visit, stored in `st.session_state` for
that browser session and used as the key into `progress.db`. Two people
typing the same name on the same deployment share one history. This is a
reasonable trade-off for a single-classroom or personal deployment; if you
deploy this multi-tenant publicly, replace `profile.py` with real per-user
auth before trusting the streaks/badges/analytics to mean anything.
