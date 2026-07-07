# 🧠 Review Sentiment Analyzer
The Review Sentiment Analyzer is a web-based application designed to collect, analyze, and summarize customer reviews from multiple online platforms. The system leverages Artificial Intelligence (AI) and Natural Language Processing (NLP) techniques to transform large volumes of unstructured review data into meaningful insights.

This project aims to assist both consumers and businesses by providing sentiment analysis, pros and cons extraction, and visual summaries of customer feedback.

---

## ✨ Features
- **Multi-Platform Collection:** Automated dynamic data ingestion from e-commerce and service channels (Lazada, Amazon, Yelp) via headless browser scraping.
- **AI-Powered Analysis:** Linguistic evaluation extracting overall sentiment polarity (Positive, Negative, Neutral).
- **Aspect Clustering:** Automated semantic extraction and side-by-side classification of explicit "Pros" and "Cons" arrays.
- **Semantic Summarization:** High-density, natural language summaries capturing overall customer consensus using Large Language Models (LLMs).
- **Hallucination Countermeasures:** Independent, deterministic backend validation loops that programmatically verify quantitative metrics.
- **Interactive Visual Dashboard:** High-performance, reactive presentation charts providing real-time data streaming and granular metric drill-down.

---

## 📐 System Architecture
The platform is built upon a decoupled layered architecture using an asynchronous FastAPI runtime backend layer, an interactive React frontend layer, and a structured NoSQL database layer.

![System Architecture](/assets/System_Architecture.png)

---

## 📋 Prerequisites
Ensure you have the following runtimes and servers installed locally on your system before deployment:
- **Python 3.10+**
- **Node.js LTS** (v18 or higher)
- **MongoDB Community Server** (running locally on default port `27017`)

---

## ⚙️ Environment Configuration
Before running the application, you must configure the environment variables. Create a `.env` file inside the `backend/` directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
SERPAPI_KEY=your_serpapi_api_key_here
MONGO_URI=mongodb://localhost:27017/your_db_name
```

---

## 🚀 Run Locally
1. Clone Repository
```bash
git clone https://github.com/ImY1l/Review-Sentiment-Analyzer.git
cd Review-Sentiment-Analyzer
```
2. Run Backend
```bash
cd backend
uvicorn main:app
```
3. Install Dependencies
```bash
npm install
```
4. Run Frontend
```bash
cd frontend
npm run dev
```
5. Access the App
```bash
Browse to http://127.0.0.1:8000
```

---

## 📚 Project Documentation
For a deep dive into the formal academic deliverables, system validation, and comprehensive technical specifications, explore the [`docs/`](./docs) directory:

- 📄 **[Final Project Report](./docs/Final_Report_Yousef.pdf)** – Complete thesis outlining methodology, architectural design choices, and testing results.
- 🎨 **[Poster Presentation](./docs/Poster_Presentation.pdf)** – The finalized A1 presentation poster layout utilized for evaluation.
- 💼 **[Commercialization Proposal](./docs/Commercialization_Proposal.pdf)** – A strategic business roadmap detailing the platform's value proposition, target market analysis, and revenue models for enterprise SaaS scaling.

---

## 👤 Author
**Mohammed Yousef Mohammed Abdulkarem**
| Detail | Information |
|--------|-------------|
| **Program** | Bachelor of Computer Science (Software Engineering) |
| **University** | Faculty of Computing and Informatics, Multimedia University, Malaysia |
| **Supervisor** | Ms. Shahbe Binti Mat Desa |
| **Project Code** | FYP02-SE-T2610-0503 |
| **Academic Year** | 2026 |

---

## ⚖️ License

© 2026 Mohammed Yousef Mohammed Abdulkarem. All Rights Reserved.

This project is submitted in partial fulfillment of the requirements for the degree of **Bachelor of Computer Science (Software Engineering)** at Multimedia University, Malaysia.

---

## 🙏 Acknowledgements
- **Ms. Shahbe Binti Mat Desa** - Project supervision and guidance
- **Faculty of Computing and Informatics** - Academic support and resources
- **Google** - Gemini LLM API for generative semantic analysis
- **Open Source Community** - FastAPI, React, Playwright
- **MongoDB** - Source-available NoSQL document database engine for robust data storage

---

## 📧 Contact
For technical inquiries, validation reviews, or questions regarding this repository:

- **GitHub**: [@ImY1l](https://github.com/ImY1l)
- **Email**: [yousef.mohammed77@outlook.com](mailto:yousef.mohammed77@outlook.com)

---

<div align="center">
  <sub>Built with ❤️ for FYP02-SE-T2610-0503 | Multimedia University 2026</sub>
</div>

[![](https://visitcount.itsvg.in/api?id=IMy1l.&icon=0&color=0)](https://visitcount.itsvg.in)
