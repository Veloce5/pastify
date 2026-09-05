# Pastify — Refactor Migration Notes

## Run it
```bash
pip install -r requirements.txt
streamlit run Home.py
```
Copy your real `past_papers.db` into this folder (the one included here is
your original, unmodified file — schema untouched, nothing was written to it).

## File mapping (old → new)

| Old file(s) | New file | What changed |
|---|---|---|
| `home.py` | `Home.py` | Manual `session_state["current_page"]` if/elif routing → native `st.navigation` / `st.Page`. |
| `filter_logic.py` | `database.py` | 8 near-duplicate getters → one generic, `@st.cache_data`-cached `get_distinct_values()`. Connection is `@st.cache_resource`. |
| `doubly_linked_list.py` + `doubly_linked_list_quiz.py` | `linked_list.py` | One implementation; payload shape is just whatever tuple the caller stores. |
| `Utils.py` | `utils.py` | PDF→image rendering now cached (`@st.cache_data` keyed on path+mtime) — this was the single biggest performance win, since PyMuPDF was previously re-rasterizing on every rerun. |
| `theme_management.py` | `theme.py` | **Bug fix**: old version wrote a *global* `~/.streamlit/config.toml`, so one user's dark-mode toggle changed the theme for every concurrent user, and needed a restart to reliably apply. New version injects per-session CSS variable overrides — instant, isolated, no disk writes. |
| `animations.py` + the `options_quiz`/`options_test` functions in `display.py` | `feedback.py` | Full-width HTML blocks → `st.toast`. **Bug fix**: answers were previously uncapped — clicking A/B/C/D repeatedly on the same question re-incremented the score every time; answers are now locked per question. |
| `display.py`'s paper-detail/snippet functions | `components.py` (`render_paper_detail_card`) | Unified; both Browse and Quiz used a near-identical version. |
| The duplicated sidebar filter block in `app.py`, `quiz.py`, `worksheet.py`, `timed_test.py` | `components.py` (`render_filter_sidebar`) | ~120 lines × 4 pages → one parameterized function. |
| `app.py` | `pages_src/browse.py` | Same feature set, new empty states, cached rendering, disabled-state buttons instead of dead clicks. |
| `worksheet.py` | `pages_src/worksheet.py` | Merge output now returned as in-memory bytes (no temp files left on disk) and offered as a single zip download. |
| `quiz.py` | `pages_src/quiz.py` | Instant per-question toast feedback + a live "progress this session" dashboard. |
| `timed_test.py` + `timed_test_selection.py` | `pages_src/timed_test.py` | **Bug fix**: the old timer used a blocking `while True: sleep(1)` loop inside the main script — meaning Next/Previous/answer buttons couldn't be clicked at all while a test was "running" (the script never finished a run, so no new interaction could be processed). Replaced with `st.fragment(run_every="1s")`, Streamlit's native self-refreshing region, which updates the countdown without blocking the page. Duration presets use the built-in `st.segmented_control`, dropping the unused `streamlit_extras` dependency entirely. Also added a locked results dashboard at time-up. |
| `aboutus.py` | `pages_src/about.py` | Same content, theme-safe. |
| new | `config.py` | Central `SESSION_KEYS` registries so every "Reset" button clears the *same* set of keys — the old app's reset lists had drifted out of sync between pages (e.g. `timed_test.py`'s list was missing keys `app.py`'s had). |

## Other correctness fixes made along the way
- `timed_test.py` previously called `get_difficulties(...)` without ever importing it — a latent `NameError` waiting to fire once a user reached that step. Gone now (unified query layer).
- Quiz/Timed Test score could be inflated by clicking an answer button multiple times on one question; answers now lock after the first click.
- Worksheet merge no longer leaves `merged_question_paper.pdf` / `merged_answer_sheet.pdf` files on disk — everything is done in memory and streamed as a zip.
- Dark mode toggle is now per-browser-tab instead of a global, file-based setting shared by every visitor.

## Notes / things to double check on your machine
- `st.fragment(run_every=...)` and `st.segmented_control` require **Streamlit ≥ 1.37** (`requirements.txt` reflects this) — if you're pinned to an older version, upgrade or tell me and I'll swap in a compatible fallback.
- I wasn't able to run this against a live Streamlit server in this sandbox (no network access here), so please smoke-test the Quiz/Timed Test flows end-to-end before deploying — I've reviewed the logic carefully but a live click-through is worth doing.
- The PDF paths in your `past_papers.db` are absolute Windows paths (e.g. `C:/Users/.../output_questions/...`); the app's PDF rendering will show a clean "file not found" empty state for any that don't resolve on the deployment machine, rather than crashing.

## Update — portable file paths (Mac / cloud-ready)

`past_papers.db` used to store absolute Windows paths in `Question`/`Answer`
(`C:/Users/Projects/TPP/output_questions/...`), which is why PDFs showed
"missing from disk" once the app moved to a Mac.

1. **Run once, locally, against your real `past_papers.db`:**
   ```bash
   python clean_db.py --db past_papers.db --dry-run   # preview first
   python clean_db.py --db past_papers.db             # apply (auto-backs-up the .db first)
   ```
   This strips everything up to and including `output_questions/`, leaving
   pure relative paths like `qp/9618/2024/May_June/12/1(a).pdf`. It's
   idempotent (safe to re-run) and never touches the quiz-mode rows whose
   `Answer` column holds a literal letter (`A`-`D`) instead of a path.
   **Note:** when I dry-ran this against the db you originally uploaded, 3
   of 11,043 rows were flagged — their *original* paths were missing the
   `qp/`/`ms/` segment entirely (e.g. `.../output_questions/9702/2013/...`),
   which is a pre-existing data issue, not something the migration caused.
   Check the flagged output and fix those rows by hand.

2. **`config.py`** now defines `OUTPUT_DIR = APP_DIR / "output_questions"`
   and a single `resolve_media_path()` function — the only place a
   relative DB path ever becomes an absolute filesystem path. Point
   `OUTPUT_DIR` wherever your media actually lives on each machine/deploy
   target (a local folder today, a mounted cloud volume later) — nothing
   downstream needs to change.

3. **`utils.py` / `database.py`** now resolve every path through
   `resolve_media_path()` right before touching disk (PDF rendering, PDF
   merging), and check `Path.exists()` on the *resolved* path — never on
   the raw DB string. No `.find()` / string-slicing anywhere anymore.
