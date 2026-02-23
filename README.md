# 🎓 AI StudyMate

**An AI-powered study assistant that transforms your documents into an interactive learning experience.**

Upload your study materials (PDFs, DOCX, TXT) and let AI help you learn through intelligent Q&A, auto-generated exams, flashcards, and quiz mode — all grounded in your own content with zero hallucinations.

> 📚 **Academic Project** — Developed as part of a personal project at [Factoria F5](https://factoriaf5.org/). Everyone is welcome to fork, use, and evolve this system. Contributions are encouraged!

---

## ✨ Features

### 📄 Document Management
- **Multi-format upload**: PDF (with OCR for scanned pages), DOCX, ODT, TXT
- **Hierarchical organization**: Workspace → Course → Subject → Topic
- **Background processing**: Automatic text extraction, chunking, and embedding
- **Cloud storage**: Optional Supabase integration for file persistence

### 🤖 AI Study Chat (RAG)
- **Retrieval-Augmented Generation**: Answers grounded exclusively in your uploaded documents
- **No-hallucination guard**: If no relevant context is found, the AI says so instead of making things up
- **Clickable source links**: Every answer shows which documents were used, with direct download links
- **Scoped queries**: Search within a specific subject, an entire workspace, or all your documents
- **Quiz Mode**: Toggle to quiz mode — the AI generates questions from your materials and evaluates your answers with scoring and feedback

### 📝 Exam Generation
- **Auto-generated exams**: Multiple choice and short answer questions from your study materials
- **Configurable difficulty**: Easy, medium, or hard
- **LLM evaluation**: Short answers are evaluated by AI with partial credit and constructive feedback
- **Attempt tracking**: Review past exam results and track progress

### 🃏 Flashcards
- **AI-generated flashcards**: Automatically created from your documents
- **Spaced repetition**: Built-in SRS with ease factor and review scheduling
- **Difficulty levels**: Easy, medium, hard

### 📊 Analytics Dashboard
- **Study streak tracking**: Consecutive days of study activity
- **Exam score trends**: Performance over time with charts
- **Weak topic detection**: Identifies areas that need more attention
- **Mastery distribution**: New / Learning / Mastered flashcard breakdown
- **Personalized recommendations**: Rule-based study tips

### ⚙️ Settings
- **LLM provider selection**: Choose between Groq, Google Gemini, or local Ollama
- **Per-user configuration**: Each user can select their preferred AI provider

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────────────────┐
│   React + TS    │────▶│  FastAPI (Python)                 │
│   Vite + TW4    │     │                                  │
│   Port 3000     │     │  ├── Auth (JWT)                  │
└─────────────────┘     │  ├── Documents (upload/process)  │
                        │  ├── RAG (chat + quiz)           │
                        │  ├── Exams (generate/evaluate)   │
                        │  ├── Flashcards (generate/SRS)   │
                        │  ├── Analytics (aggregated SQL)  │
                        │  └── Settings (LLM provider)     │
                        │                                  │
                        │  Services:                       │
                        │  ├── EmbedderService (sentence-  │
                        │  │   transformers, local)        │
                        │  ├── VectorStore (ChromaDB)      │
                        │  ├── LLMClient (Groq/Gemini/     │
                        │  │   Ollama with auto-fallback)  │
                        │  └── StorageService (local +     │
                        │      optional Supabase)          │
                        │                                  │
                        │  Port 8000                       │
                        └──────────┬───────────────────────┘
                                   │
                        ┌──────────┴───────────────────────┐
                        │  PostgreSQL (Supabase)           │
                        │  ChromaDB (embedded, persistent) │
                        └──────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Vite, TailwindCSS v4 |
| **Backend** | FastAPI, Python 3.11+, SQLAlchemy, Alembic |
| **Database** | PostgreSQL (Supabase), ChromaDB (vector store) |
| **AI/ML** | sentence-transformers (embeddings), Groq / Gemini / Ollama (LLM) |
| **Auth** | JWT (HS256) with bcrypt password hashing |
| **Storage** | Local filesystem + optional Supabase Storage |
| **DevOps** | Docker Compose, multi-service orchestration |

---

## 🚀 Quick Start

### Prerequisites

- **Docker** and **Docker Compose** installed
- A **PostgreSQL database** (Supabase free tier works great)
- At least one **LLM API key**: [Groq](https://console.groq.com) (free), [Google Gemini](https://aistudio.google.com/apikey) (free), or [Ollama](https://ollama.ai) (local)

### 1. Clone the repository

```bash
git clone https://github.com/GHalfbbt/ai-studymate.git
cd ai-studymate
```

### 2. Configure environment variables

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and fill in your values:

```env
# Required
DATABASE_URL=postgresql://postgres:PASSWORD@HOST:5432/postgres
JWT_SECRET_KEY=your-secret-key-at-least-32-chars

# At least one LLM provider
GROQ_API_KEY=your-groq-api-key
# or
GEMINI_API_KEY=your-gemini-api-key
# or install Ollama locally
```

### 3. Start with Docker Compose

```bash
docker compose up --build
```

This starts:
- **Backend** at `http://localhost:8000` (API docs at `/docs`)
- **Frontend** at `http://localhost:3000`
- Automatic database migrations via Alembic

### 4. Try it out

1. Open `http://localhost:3000`
2. Register a new account or use the demo: `demo@studymate.ai` / `demo1234`
3. Create a workspace → course → subject
4. Upload study documents (PDF, DOCX, TXT)
5. Wait for processing to complete
6. Start chatting, generating exams, or creating flashcards!

---

## 🛠️ Development Setup (without Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 📁 Project Structure

```
ai-studymate/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints (auth, documents, rag, exams, flashcards, analytics, settings)
│   │   ├── core/            # Config, database, security
│   │   ├── models/          # SQLAlchemy models (user, workspace, course, subject, document, exam, flashcard)
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic (embedder, vector_store, llm_client, ingestor, exam_generator, flashcard_generator)
│   │   └── utils/           # Extractors, chunkers, validators
│   ├── alembic/             # Database migrations
│   ├── tests/               # Pytest test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/             # API client services (axios + JWT interceptor)
│   │   ├── components/      # Reusable UI components (Layout, Upload, Spinner)
│   │   ├── pages/           # Page components (Dashboard, Chat, Exams, Flashcards, Analytics, Settings, Workspaces)
│   │   ├── store/           # Zustand state management (auth, workspace)
│   │   ├── types/           # TypeScript type definitions
│   │   └── utils/           # Formatters and helpers
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 🔑 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/auth/login` | Login (returns JWT) |
| `GET` | `/api/v1/workspaces/` | List workspaces |
| `POST` | `/api/v1/documents/upload` | Upload document |
| `GET` | `/api/v1/documents/list` | List documents |
| `GET` | `/api/v1/documents/{id}/download` | Download document |
| `POST` | `/api/v1/rag/query` | AI chat query (chat / quiz / quiz_evaluate modes) |
| `POST` | `/api/v1/exams/generate` | Generate exam from documents |
| `POST` | `/api/v1/exams/{id}/submit` | Submit exam answers |
| `POST` | `/api/v1/flashcards/generate` | Generate flashcards |
| `GET` | `/api/v1/analytics/overview` | Analytics KPIs |
| `GET` | `/api/v1/analytics/details` | Analytics chart data |
| `PATCH` | `/api/v1/settings/llm-provider` | Update LLM provider |

Full interactive docs available at `http://localhost:8000/docs`

---

## 🤖 LLM Provider Support

AI StudyMate supports multiple LLM providers with automatic fallback:

| Provider | Type | Cost | Setup |
|----------|------|------|-------|
| **Groq** | Cloud | Free tier (100k tokens/day) | Get API key at [console.groq.com](https://console.groq.com) |
| **Google Gemini** | Cloud | Free tier (generous limits) | Get API key at [aistudio.google.com](https://aistudio.google.com/apikey) |
| **Ollama** | Local | Free (unlimited) | Install [Ollama](https://ollama.ai) and run `ollama pull llama3` |

The system automatically falls back to the next available provider if one fails or hits rate limits.

---

## 🧪 Running Tests

```bash
cd backend
pytest -v
```

---

## 🤝 Contributing

This is an **open academic project** and contributions are very welcome! Whether you want to:

- 🐛 Fix bugs
- ✨ Add new features
- 📖 Improve documentation
- 🎨 Enhance the UI/UX
- 🌍 Add translations
- 🧪 Write tests

Feel free to:

1. **Fork** the repository
2. Create a **feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'feat: add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. Open a **Pull Request**

### Ideas for Future Development

- 🎙️ Voice practice mode (speech-to-text + evaluation) — *partially scaffolded, coming soon*
- 📱 Mobile-responsive PWA
- 🌐 Multi-language support
- 📊 Advanced analytics with ML-based predictions
- 👥 Collaborative study groups
- 🔗 Integration with LMS platforms (Moodle, Canvas)
- 📤 Export exams to PDF/DOCX
- 🧠 Advanced spaced repetition algorithms (SM-2, FSRS)

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this software for any purpose, including commercial use.

---

## 🙏 Acknowledgments

- [Factoria F5](https://factoriaf5.org/) — For the educational framework and support
- [Groq](https://groq.com/) — For fast, free LLM inference
- [Google Gemini](https://ai.google.dev/) — For generous free-tier AI access
- [Supabase](https://supabase.com/) — For the excellent PostgreSQL hosting and storage
- [ChromaDB](https://www.trychroma.com/) — For the embedded vector database
- [sentence-transformers](https://www.sbert.net/) — For local embedding generation

---

<p align="center">
  Made with ❤️ for students, by students
</p>
