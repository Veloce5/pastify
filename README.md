# Pastify

**An interactive Cambridge A-Level past-paper platform built for targeted practice, timed testing, and measurable progress.**

Pastify transforms static past-paper PDFs into a structured learning experience where students can find exactly what they need, practice questions interactively, build custom worksheets, take timed tests, and track their performance over time.

Built with **Python, Streamlit, SQLite, PyMuPDF, PyPDF2, and Plotly**.

---

## 🚀 What is Pastify?

Cambridge A-Level students often have access to large collections of past papers, but finding the *right* question for targeted practice can be difficult when everything is stored as static PDFs.

Pastify solves this by processing examination papers into structured question data and providing an interface for searching, filtering, practicing, and tracking progress.

Instead of manually searching through hundreds of PDF pages, students can filter questions by criteria such as:

* Subject
* Topic
* Year
* Variant
* Paper
* Difficulty

They can then move directly from finding a question to practicing it, adding it to a worksheet, taking a quiz, or using it as part of a timed test.

---

## ✨ Features

### 🔎 Advanced Paper Filtering

Use cascading filters to quickly narrow down thousands of questions.

Filter by:

* Subject
* Topic
* Year
* Variant
* Paper
* Difficulty
* Keywords

Filters adapt to the current selection, helping students find relevant questions without manually searching through PDFs.

---

### 📝 Interactive Quizzes

Practice Cambridge Paper 1 multiple-choice questions through an interactive quiz interface.

Features include:

* A/B/C/D answer selection
* Answer locking
* Immediate feedback
* Question navigation
* Score tracking
* Attempt history
* Topic-level performance data

---

### ⏱️ Timed Test Simulator

Create a timed practice session with configurable:

* Test duration
* Number of questions
* Subject
* Topic
* Year
* Variant
* Difficulty

The countdown timer runs independently from the rest of the application UI, keeping the interface responsive during the test.

---

### 📄 Worksheet Builder

Build a custom worksheet from individual questions.

Students can:

1. Browse questions
2. Add selected questions to a worksheet
3. Review their selection
4. Generate a combined PDF
5. Export the resulting worksheet

This turns Pastify from a simple question browser into a practical revision tool.

---

### 📊 Progress Analytics

Pastify records practice attempts and turns them into useful performance information.

The progress system includes:

* Attempt history
* Accuracy
* Topic performance
* Daily activity
* Practice streaks
* Question pacing
* Badges and achievement thresholds

Performance data is visualized using Plotly.

---

### 🏆 Gamification

Pastify includes a lightweight gamification layer designed to encourage consistent practice.

Students can build:

* Practice streaks
* Achievement badges
* Accuracy milestones
* Activity history

---

### 🌙 Theme Support

Pastify includes a custom theme system with support for light and dark interfaces, using shared CSS variables and reusable styling components.

---

# 🏗️ Architecture

Pastify is structured into separate layers rather than placing application logic directly inside individual Streamlit pages.

```text
                         ┌─────────────────────┐
                         │      Home.py        │
                         │ Streamlit Entry Point│
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
       │ Page Layer  │       │ Components  │       │   Theme /   │
       │             │       │  & Feedback │       │    Styles   │
       └──────┬──────┘       └──────┬──────┘       └─────────────┘
              │                     │
              └─────────────┬───────┘
                            ▼
                   ┌─────────────────┐
                   │ Application     │
                   │ Logic & State   │
                   └────────┬────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
      ┌─────────────────┐         ┌─────────────────┐
      │ Database Layer  │         │ Progress Engine │
      │   database.py   │         │   progress.py   │
      └────────┬────────┘         └────────┬────────┘
               │                           │
               ▼                           ▼
       ┌─────────────────┐         ┌─────────────────┐
       │ past_papers.db  │         │   progress.db   │
       └─────────────────┘         └─────────────────┘
```

This separation allows individual parts of the application to evolve without requiring every page to contain its own database, state, or UI logic.

---

# ⚡ Performance Engineering

Pastify works with a large collection of PDF-based question assets, so responsiveness is an important part of the architecture.

### SQLite Indexing

The database initialization layer ensures indexes exist on frequently queried fields such as:

* Subject
* Topic
* Year
* Variant
* Paper
* Question path

This improves performance for the application's multi-stage filtering system.

### Streamlit Caching

Expensive operations are cached using Streamlit's caching mechanisms.

Database queries use `st.cache_data`, while the database connection is managed through `st.cache_resource`.

### Smart PDF Rendering Cache

Rendered PDF pages are cached using the resolved file path, file modification time, and rendering configuration.

This means a PDF does not need to be rendered again when the underlying file has not changed.

### UI Fragments

Interactive operations that would otherwise trigger larger Streamlit reruns are isolated using `st.fragment`.

This is used for components such as:

* Answer feedback
* The timed-test countdown
* Other frequently changing interactive state

The result is a more responsive experience without repeatedly rebuilding the entire page.

---

# 📄 Advanced PDF Processing Pipeline

One of the core engineering components of Pastify is `split_papers.py`.

Rather than treating examination papers as simple documents that can be split using fixed string positions, Pastify uses a multi-stage extraction pipeline designed around the structure of Cambridge examination PDFs.

### Filename & Question Parsing

Metadata is extracted from Cambridge's examination-paper naming conventions.

This allows question files to be associated with information such as:

* Subject
* Session
* Year
* Variant
* Paper
* Question number

### Multiple-Choice Question Detection

Multiple-choice mark schemes require different handling from written-answer mark schemes.

The extraction pipeline therefore includes dedicated processing logic for MCQ material.

### Hierarchical Anchor Detection

When locating question boundaries, the pipeline can progressively fall back through different levels of PDF text structure.

```text
Block
  ↓
Line
  ↓
Span
```

This provides additional resilience when a standard text anchor cannot be found.

### Zero-Drop Fallbacks

The extraction process includes fallback handling and page-range validation intended to prevent questions from silently disappearing when the expected PDF structure is not detected.

---

# 🗂️ Project Structure

```text
Pastify/
│
├── Home.py
│
├── pages_src/
│   ├── about.py
│   ├── browse.py
│   ├── landing.py
│   ├── my_progress.py
│   ├── quiz.py
│   ├── timed_test.py
│   └── worksheet.py
│
├── analytics.py
├── components.py
├── config.py
├── database.py
├── feedback.py
├── linked_list.py
├── profile.py
├── progress.py
├── split_papers.py
├── styles.css
├── theme.py
├── utils.py
│
├── clean_db.py
├── requirements.txt
│
├── README.md
└── .gitignore
```

### Key Modules

| File              | Purpose                                                           |
| ----------------- | ----------------------------------------------------------------- |
| `Home.py`         | Main Streamlit entry point and page navigation                    |
| `pages_src/`      | Individual application pages                                      |
| `components.py`   | Reusable UI components and filter interface                       |
| `database.py`     | SQLite connection, filtering, and query operations                |
| `progress.py`     | Attempt history, streaks, badges, and performance tracking        |
| `analytics.py`    | Progress visualization and analytics                              |
| `feedback.py`     | Quiz answer handling, scoring, and feedback                       |
| `linked_list.py`  | Doubly linked list used for question traversal                    |
| `split_papers.py` | PDF ingestion and question extraction pipeline                    |
| `utils.py`        | PDF rendering, merging, ZIP creation, and utility functions       |
| `config.py`       | Application paths, constants, database configuration, and indexes |
| `theme.py`        | Theme management and CSS handling                                 |
| `styles.css`      | Custom application styling                                        |
| `clean_db.py`     | Database cleaning and maintenance utility                         |

---

# 🛠️ Tech Stack

### Application

* **Python**
* **Streamlit**

### Data & Storage

* **SQLite**
* **Streamlit caching**
* Separate databases for paper content and user progress

### PDF Processing

* **PyMuPDF**
* **PyPDF2**

### Visualization

* **Plotly**

### Frontend

* Streamlit components
* Custom CSS
* Responsive UI elements
* Light/dark theme system

---

# 🚀 Installation & Setup

## 1. Clone the repository

```bash
git clone https://github.com/Veloce5/pastify.git
cd pastify
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Add the required data

Pastify requires the application's paper database and processed PDF assets.

Place:

```text
past_papers.db
```

and the processed PDF files inside:

```text
output_questions/
```

The repository does not include the full paper dataset.

## 4. Launch Pastify

```bash
streamlit run Home.py
```

The application should then open in your browser.

---

# 🧪 Testing

Automated testing is an ongoing part of Pastify's development.

The most important areas for testing include:

* Database filtering
* PDF filename parsing
* Question extraction
* Question navigation
* Progress calculations
* Streak calculations
* Badge thresholds
* PDF utilities

Run the test suite with:

```bash
pytest
```

> If you have not yet added the `tests/` directory, this section can be added when the automated test suite is introduced.

---

# 🔧 Design Decisions

## Why SQLite?

Pastify's paper data is primarily read-heavy and structured around filtering and retrieval.

SQLite provides a lightweight relational database without requiring a separate database server, making it well suited to the application's current architecture.

Indexes are created for frequently queried fields to improve filtering performance.

## Why Separate Progress Storage?

Past-paper content and student-generated progress data have different purposes.

```text
past_papers.db
     │
     └── Question & paper metadata

progress.db
     │
     └── Attempts & learning progress
```

Separating these concerns makes it easier to keep the core paper dataset read-focused while allowing progress data to change frequently.

## Why a Doubly Linked List?

Question-based interfaces frequently require moving between the current question, the previous question, and the next question.

The custom `DoublyLinkedList` implementation provides a centralized abstraction for this traversal rather than duplicating navigation logic across quiz and test interfaces.

---

# 📈 Future Roadmap

Pastify is an evolving project.

### Completed

* [x] Advanced cascading filters
* [x] Interactive Paper 1 quizzes
* [x] Timed test simulator
* [x] Worksheet builder
* [x] Progress tracking
* [x] Topic analytics
* [x] Streaks and badges
* [x] PDF question extraction pipeline
* [x] Light/dark theme support

### Planned

* [ ] Expand subject coverage
* [ ] Increase automated test coverage
* [ ] Improve accessibility
* [ ] Expand analytics
* [ ] Further optimize PDF processing
* [ ] Continue improving the question database
* [ ] Production deployment improvements

---

# 👥 Team

Pastify is developed collaboratively.

### Dev Joshi

**Co-Founder & Backend Lead**

Responsible for backend architecture, database systems, PDF processing, application logic, and performance-focused development.

### Veer Sanghvi

**Co-Founder & Frontend Lead**

Responsible for the frontend experience, interface design, and user-facing application development.

---

# 📸 Application Preview

> Add screenshots or a short GIF of the application here.

Recommended screenshots:

1. **Landing Page** — Overall Pastify experience
2. **Browse** — Cascading filters and question selection
3. **Quiz** — Interactive question and answer feedback
4. **Timed Test** — Countdown timer and test interface
5. **My Progress** — Analytics, activity, streaks, and badges
6. **Worksheet Builder** — Custom question collection and export

---

# 📄 License

This project is currently maintained as a personal/educational software project.

Add a formal open-source license here if you intend to distribute the source code under specific reuse terms.

---

## ⭐ About Pastify

Pastify was built around a simple idea:

**Past papers are one of the most valuable resources available to A-Level students — they should be easier to search, practice, and learn from.**

By combining structured question data, intelligent filtering, interactive practice, PDF processing, analytics, and gamification, Pastify turns a collection of static examination papers into a more usable learning platform.
