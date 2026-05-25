# JobInterview

> **Paste a job description. Get a real mock interview. Walk in ready.**

JobInterview generates 6 tailored interview questions from any job description, scores your answers live with AI coaching feedback, and finishes with a full performance report and action plan.

![status](https://img.shields.io/badge/status-complete-brightgreen)
![stack](https://img.shields.io/badge/stack-FastAPI%20%C2%B7%20Groq%20%C2%B7%20Llama%203.3-blueviolet)

## How it works

1. **Paste the job description** — the AI reads the role, tech stack, and requirements
2. **Answer 6 tailored questions** — a mix of behavioural, technical, situational, and motivation questions
3. **Get live feedback** — every answer is scored 1–10 with what was good, what to improve, and a pro tip
4. **Receive a full report** — overall score, top strengths, top weaknesses, action plan, and hire likelihood

## Stack

- **FastAPI** + Uvicorn — Python web framework
- **Groq** (`llama-3.3-70b-versatile`) — fast LLM for question generation, answer evaluation, and report writing
- **pydantic-settings** — typed, validated configuration from environment variables
- **Vanilla JS + Jinja2** — frontend, no build step required

## Project layout

```
JobInterview/
├── main.py           FastAPI app — routes, LLM calls, request models
├── config.py         Typed settings (pydantic-settings)
├── requirements.txt
├── Procfile          For Render / Railway deploy
├── .env.example      Template for API keys
├── .gitignore
├── README.md
├── templates/
│   └── index.html    Single-page interview UI
└── static/
    ├── css/
    └── js/
```

## Quick start

### 1. Get a Groq API key
Sign up for free at [console.groq.com](https://console.groq.com/keys).

### 2. Install

```bash
cd JobInterview
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env    # Windows
# cp .env.example .env    # macOS / Linux
```

Open `.env` and paste your Groq API key.

### 3. Run

```bash
uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) and paste any job description to start.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Landing page |
| `POST` | `/generate-questions` | Generate 6 interview questions |
| `POST` | `/evaluate-answer` | Score one answer with feedback |
| `POST` | `/generate-report` | Final performance report |

### Score guide
| Score | Label |
|-------|-------|
| 1–3 | Weak |
| 4–6 | Average |
| 7–8 | Strong |
| 9–10 | Excellent |

## Deployment

The `Procfile` works out of the box on Render, Railway, and Fly.io.
Set `GROQ_API_KEY` in your host's environment variables dashboard.

## License

MIT — built by Martin Genov.
