<div align="center">

# 📚 Pastify

### Past papers, made practical.

**An interactive Cambridge A-Level revision platform for finding questions, building worksheets, practising under exam conditions, and tracking progress.**

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Release](https://img.shields.io/badge/Release-v1.1.0-2563eb)](https://github.com/Veloce5/pastify/releases/tag/v1.1.0)

**[🚀 Launch Pastify](https://pastify-nmnnanickpby7jtc8y6sls.streamlit.app/) · [Latest release](https://github.com/Veloce5/pastify/releases/tag/v1.1.0) · [Changelog](CHANGELOG.md) · [Report an issue](https://github.com/Veloce5/pastify/issues)**

</div>

---

## Overview

Finding a particular question in a folder of past-paper PDFs shouldn't be harder than answering it.

**Pastify** transforms Cambridge A-Level past-paper material into a searchable, interactive question bank. Instead of opening papers one by one, students can narrow down questions, assemble targeted practice, take interactive quizzes or timed tests, and review their performance.

> **Current release — v1.1.0 (MCQ Expansion):** 1,340 multiple-choice questions added, bringing the question bank to **12,383 questions**. See the [release notes](https://github.com/Veloce5/pastify/releases/tag/v1.1.0).

## Features

| Feature | What it does |
| --- | --- |
| 🔎 **Browse Papers** | Filter questions by subject, topic, year, paper, variant, difficulty, and keywords. |
| 📝 **Worksheet Builder** | Select questions and export a custom practice worksheet as a PDF. |
| 🎮 **Quiz Mode** | Practise supported MCQs with A–D answer selection, feedback, scoring, and question navigation. |
| ⏱️ **Timed Test** | Create timed practice sessions with configurable question selection and a countdown. |
| 📈 **My Progress** | Explore attempts, accuracy, topic-level performance, practice activity, streaks, and achievements. |
| 🎨 **Themes** | Switch between the app's custom visual themes. |
| ✨ **What's New** | View release highlights and previous updates directly in the app. |

### A closer look

**Focused discovery.** Cascading filters help students move from a large collection of papers to a targeted set of questions without manually inspecting PDF pages.

**Active practice.** Quiz Mode and Timed Test provide distinct workflows for quick revision and exam-style sessions. Questions without recorded answers are excluded from answer-checked quizzes.

**Reusable output.** Worksheet Builder lets students collect selected questions and generate a combined PDF for offline practice.

**Actionable feedback.** Progress analytics use Plotly visualizations to make patterns in attempts, accuracy, and activity easier to understand.

## Application preview

![Pastify application preview](1280x720.png)

*Repository preview image. [Explore the live app](https://pastify-nmnnanickpby7jtc8y6sls.streamlit.app/).*

## How Pastify works

```text
Cambridge examination PDFs
           │
           ▼
  PDF processing pipeline
  • Parse paper metadata
  • Detect question boundaries
  • Handle MCQ-specific layouts
  • Extract question/mark-scheme assets
           │
           ▼
      SQLite question bank
           │
           ▼
   Streamlit application
   ├── Browse Papers
   ├── Worksheet Builder
   ├── Quiz Mode
   ├── Timed Test
   └── My Progress
           │
           ▼
    Practice & analytics
```

The application uses a modular structure rather than embedding database queries, PDF processing, and UI logic in a single page.

### Engineering highlights

- **PDF extraction:** `split_papers.py` uses progressively finer text anchors (block → line → span), paper metadata parsing, MCQ-aware processing, and fallback handling for difficult layouts.
- **Dedicated MCQ utility:** `mcq_splitter.py` provides a separate command-line tool for splitting supported multiple-choice papers into individual question PDFs.
- **Hybrid PDF access:** `pdf_storage.py` supports accessing processed PDF assets through local storage and GitHub Releases, reducing reliance on bundling large PDFs with the application code.
- **Efficient queries:** SQLite indexes support common filtering operations; Streamlit caching reduces repeated database and rendering work.
- **Responsive interactions:** Streamlit fragments isolate frequently changing UI such as feedback and timed-test countdowns.
- **Separation of concerns:** Question metadata and student progress are handled through distinct application modules and data flows.

## Tech stack

| Area | Technologies |
| --- | --- |
| Application | Python, Streamlit |
| Data | SQLite |
| PDF processing | PyMuPDF, PyPDF2 |
| Analytics | Plotly |
| Interface | Streamlit components, custom CSS, theme management |
| Asset delivery | Local PDF files, GitHub Releases |

## Try it online

**[Open Pastify on Streamlit Cloud →](https://pastify-nmnnanickpby7jtc8y6sls.streamlit.app/)**

No local setup is needed to explore the hosted application.

## Getting started

### 1. Clone the repository

```bash
git clone https://github.com/Veloce5/pastify.git
cd pastify
```

### 2. Create an environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

On Windows, activate the environment using `.venv\Scripts\activate` instead.

### 3. Check the question data and PDF assets

The repository includes the application's SQLite question database (`past_papers.db`), but **the complete collection of processed question PDFs is not stored in Git**.

PDFs are accessed using the app's configured storage mechanism, including local `output_questions/` assets and GitHub Releases-hosted assets. If you are running your own copy, confirm that the database and PDF storage settings in `config.py` and `pdf_storage.py` match the assets available to you. Some paper previews or exports may require those assets.

### 4. Start the app

```bash
python3 -m streamlit run Home.py
```

Open the local address shown in the terminal (usually `http://localhost:8501`).

> **Deployment:** The hosted application is maintained on the `hosting-ready` branch. `main` is the primary development/reference branch.

## Repository guide

```text
pastify/
├── Home.py                  # Streamlit entry point and navigation
├── pages_src/               # App pages, including What's New
├── components.py            # Reusable interface components
├── database.py              # Question-bank access and filtering
├── analytics.py             # Progress analytics
├── progress.py              # Progress and achievement logic
├── feedback.py              # Answers and scoring feedback
├── profile.py               # User profile initialization
├── theme.py                 # Theme synchronization
├── styles.css               # Custom styling
├── config.py                # Paths and application configuration
├── utils.py                 # PDF rendering and other utilities
├── pdf_storage.py           # Local and remote PDF access
├── split_papers.py          # General question extraction pipeline
├── mcq_splitter.py          # Standalone Cambridge MCQ splitter
├── past_papers.db           # Question metadata database
├── requirements.txt         # Python dependencies
├── CHANGELOG.md             # Release history
└── README.md
```

### Standalone MCQ splitter

The project also includes `mcq_splitter.py`, a standalone utility for extracting individual questions from supported Cambridge multiple-choice papers.

| Subject | Syllabus code | Questions per paper |
| --- | --- | ---: |
| Physics | `9702` | 40 |
| Accounting | `9706` | 30 |
| Economics | `9708` | 30 |

**Split one paper:**

```bash
python3 mcq_splitter.py \
  --input "/path/to/question_paper.pdf" \
  --output "./split_questions"
```

**Split a directory:**

```bash
python3 mcq_splitter.py \
  --input "/path/to/question_papers" \
  --output "./split_questions"
```

Run `python3 mcq_splitter.py --help` for available options. Review extracted PDFs before using them in a question bank; unusual layouts may require manual inspection.

## Testing and development

Pastify's key testing areas include PDF parsing and extraction, database filtering, question navigation, answer validation, progress calculations, and PDF utilities.

If the test dependencies and test suite are installed in your checkout, run:

```bash
python3 -m pytest
```

A successful Python syntax check is not a substitute for testing the interactive application with representative questions and PDF assets.

## Releases and roadmap

**v1.1.0 — MCQ Expansion**

- Added **1,340 MCQs** to the question bank (**12,383 questions total**).
- Improved MCQ PDF processing and question availability.
- Excluded questions without recorded answers from quizzes.
- Added an in-app **What's New** page.

Read the complete [changelog](CHANGELOG.md) or browse [GitHub Releases](https://github.com/Veloce5/pastify/releases).

**Areas for continued improvement:** broader subject coverage, automated test coverage, accessibility, analytics, and PDF-processing reliability.

## Team

| Contributor | Role | Focus |
| --- | --- | --- |
| **Dev Joshi** | Co-Founder & Backend Lead | Architecture, databases, PDF processing, application logic, performance |
| **Veer Sanghvi** | Co-Founder & Frontend Lead | Interface design, frontend experience, user-facing workflows |

## Project status and usage

Pastify is an independently developed educational project. Examination papers and mark schemes belong to their respective rights holders; this repository's availability does not grant rights to redistribute third-party materials.

**No open-source license is currently specified in this repository.** Until a license is added, do not assume the source code is licensed for unrestricted reuse or redistribution.

---

<div align="center">

**Built to make past-paper practice more focused, flexible, and useful.**

[Back to top](#-pastify) · [View v1.1.0](https://github.com/Veloce5/pastify/releases/tag/v1.1.0)

</div>
