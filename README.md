# Pastify 📚

Pastify is an advanced, interactive Cambridge A-Level Past Paper platform built with Python and Streamlit. It allows students to instantly filter, compile, and test themselves on thousands of past paper questions.

The backend dynamically resolves localized paper snippets and mark schemes, offering an incredibly fast, portable, and data-driven approach to exam preparation.

## 🚀 Core Features

* **Advanced Cascading Filters:** Instantly query papers by Subject, Topic, Subtopic, Year, Variant, Paper Number, and Difficulty.
* **Worksheet Builder:** Select customized sets of questions and dynamically compile them into a single, downloadable ZIP containing merged Question and Answer PDFs.
* **Interactive Quiz Mode:** A gamified environment for Paper 1 (Multiple Choice Questions) featuring answer-locking, instant validation toasts, and live scoring.
* **Timed Test Simulator:** Replicates real exam conditions with an asynchronous countdown timer and a post-test analytics dashboard breaking down accuracy by topic.

## 🛠️ Tech Stack

* **Frontend:** Streamlit, Custom CSS
* **Backend:** Python 3, PyMuPDF (fitz), PyPDF2
* **Database:** SQLite (Highly optimized, cached querying)
* **Architecture:** Modular session-state management, cached PDF byte-rendering, relative path resolution.

## 💻 Local Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR-GITHUB-USERNAME/pastify.git](https://github.com/YOUR-GITHUB-USERNAME/pastify.git)
   cd pastify