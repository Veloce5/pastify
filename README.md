Markdown
# Pastify

A high-performance, SaaS-style educational platform designed to help Cambridge A-Level students master their subjects through targeted practice. Built with Python and Streamlit, Pastify transforms static past-paper PDFs into an interactive, gamified learning engine.

---

## 📸 Application Previews

*(Replace these placeholders with actual screenshots of your app once deployed)*
* **[Screenshot 1]** - The My Progress Dashboard (Plotly Analytics)
* **[Screenshot 2]** - Filter Cascade & Worksheet Cart
* **[Screenshot 3]** - Timed Test UI with Asynchronous Timer

---

## 🏗️ Architecture

Pastify is built on a modular architecture that strictly separates the UI layer, state management, and database operations, avoiding the "spaghetti code" common in standard Streamlit apps.

```text
Streamlit Runtime (Home.py routing)
   │
   ├─► Page Layer (landing.py, browse.py, quiz.py, timed_test.py, etc.)
   │
   ├─► Components & UI Layer (components.py, feedback.py, theme.py)
   │
   ├─► State & Progress Engine (progress.py, analytics.py, linked_list.py)
   │
   ├─► Database Access Layer (database.py)
   │
   ├─► SQLite Engines (past_papers.db, progress.db)
   │
   └─► PDF Storage Directory (/output_questions)
⚡ Performance Engineering
Speed and responsiveness are critical when dealing with thousands of PDF assets. Pastify employs several advanced performance strategies:

SQLite Indexing: The config.py bootstrapper automatically ensures indexes exist for high-traffic columns (Subject, Topic, Year, Variant) to power the multi-step filter cascade instantly.

Streamlit Caching: Heavy database queries are memoized using st.cache_data, and database connections are pooled using st.cache_resource.

Smart PDF Caching: PDF rendering is cached using a composite key of the resolved path + file modification time. The UI only re-renders the PDF if the underlying file is actually modified.

UI Fragments (st.fragment): Expensive full-page re-renders are bypassed by isolating interactive components. The A/B/C/D answer feedback buttons and the asynchronous countdown timer (run_every="1s") run entirely within their own isolated fragments.

📄 Advanced PDF Extraction Pipeline
The core data generation is handled by split_papers.py, a robust ingestion pipeline rather than a simple split script.

Instead of naive string slicing, it utilizes a Multi-Tier Anchor Detection System to perfectly slice examination papers and mark schemes:

Filename & Question Parsing: Accurately extracts metadata directly from Cambridge's specific naming conventions.

MCQ Detection: Employs divergent processing logic specifically for Multiple Choice Question mark schemes, which require different bounding box handling than written answers.

Hierarchical Fallbacks: If standard text anchors fail, the algorithm falls back through a block → line → span detection hierarchy to ensure no data is lost.

Zero-Drop Fail-safes: Custom page-range calculations and mark-scheme specific handling guarantee accurate question-to-answer mapping.

🗂️ Project Structure
Home.py — The main Streamlit entry point and native st.navigation router.

/pages_src/ — Contains all isolated page views (quiz.py, timed_test.py, my_progress.py).

split_papers.py — The advanced PDF extraction and anchor-detection pipeline.

database.py — Cached SQLite query layer enforcing dynamic SQL identifier safety.

progress.py & analytics.py — Gamification engine tracking streaks, accuracy, and badge thresholds, visualized via Plotly.

feedback.py — Handles answer locking, scoring, and attempt history persistence.

linked_list.py — A generalized Doubly Linked List implementation for fluid Next/Previous question traversal.

🚀 Installation & Setup
Clone the repository and install the required dependencies to run Pastify locally:

Bash
# 1. Clone the repository
git clone [https://github.com/Veloce5/pastify.git](https://github.com/Veloce5/pastify.git)

# 2. Navigate into the project directory
cd pastify

# 3. Install the dependencies
pip install -r requirements.txt

# 4. Launch the application
streamlit run Home.py
Note: You must provide your own past_papers.db and sliced PDFs in the output_questions/ directory.