<div align="center">

# 📚 Pastify

### Past papers, made practical.

**A free, student-built revision platform for finding past-paper questions, creating worksheets, practising under exam conditions, and tracking progress.**

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Release](https://img.shields.io/badge/Release-v1.2.0-2563eb)](https://github.com/Veloce5/pastify/releases/tag/v1.2.0)

**[🚀 Launch Pastify](https://pastify-nmnnanickpby7jtc8y6sls.streamlit.app/) · [Latest release](https://github.com/Veloce5/pastify/releases/tag/v1.2.0) · [Changelog](CHANGELOG.md) · [Report an issue](https://github.com/Veloce5/pastify/issues)**

</div>

---

## Overview

Finding a particular question in a folder of past-paper PDFs shouldn't be harder than answering it.

**Pastify** is an independent, free educational project built by former Cambridge students. It organizes supported Cambridge A-Level past-paper questions into a searchable, interactive question bank. Students can narrow down questions, assemble targeted practice, take interactive quizzes or timed tests, and review their performance.

Pastify is not affiliated with or endorsed by Cambridge International. Permission to display Cambridge copyrighted examination content has been requested and is **pending**; the platform’s current availability should not be interpreted as authorization.

> **Published application release — v1.2.0 (Infrastructure & Platform Improvements):** 1,340 multiple-choice questions added, bringing the question bank to **12,383 questions**. See the [release notes](https://github.com/Veloce5/pastify/releases/tag/v1.2.0).

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

![Pastify application preview](assets/1280x720.png)

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

- **PDF extraction:** `tools/database/split_papers.py` uses progressively finer text anchors (block → line → span), paper metadata parsing, MCQ-aware processing, and fallback handling for difficult layouts.
- **Dedicated MCQ utility:** `tools/mcq/mcq_splitter.py` provides a separate command-line tool for splitting supported multiple-choice papers into individual question PDFs.
- **Private PDF storage:** `pdf_storage.py` and `private_pdf_storage.py` support retrieving processed PDF assets from an access-controlled GitHub Releases repository. Local storage is also supported for development. The PDF archives and access credentials are not distributed with the public source repository.
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
| Asset delivery | Local files or authenticated private GitHub Releases |

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

The hosted application retrieves processed question PDFs from **private GitHub Releases storage** using server-side credentials. Public GitHub Releases no longer host the bulk PDF archives. A public clone does **not** include those private assets or credentials, so PDF-dependent previews, worksheets, and other features may not work without separately authorized materials.

For local development with materials you are authorized to use, configure the local PDF directory and set `PDF_STORAGE_MODE=local`. The hosted deployment uses `PDF_STORAGE_MODE=github_private_zip` with the private repository, release tag, and read token supplied through **Streamlit secrets**, not committed files. Relevant configuration keys are `GITHUB_PRIVATE_PDF_REPO`, `GITHUB_PRIVATE_PDF_RELEASE_TAG`, and `GITHUB_PDF_READ_TOKEN`.

**Security:** Never commit GitHub tokens, Streamlit secrets, private archives, or credentials to this repository. Private storage restricts access to the archives but does not itself grant copyright permission to display individual examination questions.

### 4. Start the app

```bash
python3 -m streamlit run Home.py
```

Open the local address shown in the terminal (usually `http://localhost:8501`).

> **Deployment:** Streamlit Cloud deploys the `hosting-ready` branch with `Home.py` as the entry point. Development changes are committed to `main` and synchronized to `hosting-ready` for deployment.

## Repository guide

The application code lives in the repository root and `pages_src/`. Assets and screenshots are in `assets/`, database utilities in `tools/database/`, MCQ utilities in `tools/mcq/`, historical crop scripts in `tools/mcq/legacy/`, migration notes in `docs/`, and local development archives in `archive/`.

The tracked `past_papers.db` supports the existing application. Generated PDFs and local progress data are excluded from Git.

### Standalone MCQ splitter

The project also includes `tools/mcq/mcq_splitter.py`, a standalone utility for extracting individual questions from supported Cambridge multiple-choice papers.

| Subject | Syllabus code | Questions per paper |
| --- | --- | ---: |
| Physics | `9702` | 40 |
| Accounting | `9706` | 30 |
| Economics | `9708` | 30 |

**Split one paper:**

```bash
python3 tools/mcq/mcq_splitter.py \
  --input "/path/to/question_paper.pdf" \
  --output "./split_questions"
```

**Split a directory:**

```bash
python3 tools/mcq/mcq_splitter.py \
  --input "/path/to/question_papers" \
  --output "./split_questions"
```

Run `python3 tools/mcq/mcq_splitter.py --help` for available options. Review extracted PDFs before using them in a question bank; unusual layouts may require manual inspection.

### Batch MCQ processing

The batch processor at `tools/mcq/run_mcq_batch.py` discovers eligible Cambridge MCQ papers and produces extraction reports.

Preview papers without writing files:

    python3 tools/mcq/run_mcq_batch.py --input /path/to/source_papers --output /path/to/new_staging --subjects 9702 9706 9708 --dry-run

Remove `--dry-run` only after reviewing the results. The destination must not already exist. Source folders currently follow the names `9702 Physics`, `9706 Accounting`, and `9708 Economics`. Additional subjects require testing and support in the splitter.

### Isolated MCQ integration

The published v1.1.0 release was documented as containing **12,383 questions**. A separate local integration database was documented as containing **19,103 rows**, including **6,720 additional MCQs**. These figures describe their respective datasets, not a newly announced public release.

For local integration testing, configure `PASTIFY_DB_PATH`, `PASTIFY_OUTPUT_DIR`, and `PDF_STORAGE_MODE=local` to point to the isolated database and PDF assets.

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

Pastify was created by two former Cambridge students who wanted a more practical way to revise.

| Contributor | Role | Focus | GitHub | LinkedIn |
| --- | --- | --- | --- | --- |
| **Dev Joshi** | Co-Founder & Backend Lead | Architecture, databases, PDF processing, application logic, performance | [Veloce5](https://github.com/Veloce5) | [Profile](https://www.linkedin.com/in/dev-joshi-1310ab346/) |
| **Veer Sanghvi** | Co-Founder & Frontend Lead | Interface design, frontend experience, user-facing workflows | [9958ViceVortex](https://github.com/9958ViceVortex) | [Profile](https://www.linkedin.com/in/veer-sanghvi-b34214379/) |

Learn more in the application's **About Us** page.

## Project status and usage

Pastify is an independently developed, free educational project, **not affiliated with or endorsed by Cambridge International**. Cambridge examination papers, questions, and mark schemes belong to their respective rights holders. **Written permission has been requested and is pending.** Neither publication of this repository nor use of private PDF storage grants permission to reproduce, display, or redistribute third-party materials.

**No open-source license is currently specified in this repository.** Until a license is added, do not assume the source code is licensed for unrestricted reuse or redistribution.

---

<div align="center">

**Built to make past-paper practice more focused, flexible, and useful.**

[Back to top](#-pastify) · [View v1.2.0](https://github.com/Veloce5/pastify/releases/tag/v1.2.0)

</div>
