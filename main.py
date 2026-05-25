"""JobInterview -- FastAPI application entrypoint.

Simulates a full job interview experience powered by the Groq LLM.
The user pastes a job description, receives 6 tailored questions,
answers them one at a time (with live AI feedback), and gets a full
performance report at the end.

Routes
------
GET  /                     Landing page with job description form
POST /generate-questions   Generate 6 interview questions from a JD
POST /evaluate-answer      Score one answer and give coaching feedback
POST /generate-report      Summarise the full interview with action plan
"""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import OpenAI
from pydantic import BaseModel, Field

from config import settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent

# Number of interview questions generated per session.
QUESTION_COUNT = 6

# ---------------------------------------------------------------------------
# Lazy Groq client singleton
# ---------------------------------------------------------------------------
_groq_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Return the shared Groq client, creating it on first call."""
    global _groq_client
    if _groq_client is None:
        _groq_client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )
    return _groq_client


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate config and initialise the Groq client on startup."""
    logger.info("JobInterview starting up...")
    _get_client()
    logger.info("Groq client ready (model: %s).", settings.groq_model)
    yield
    logger.info("JobInterview shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="JobInterview", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _llm(prompt: str, temperature: float = 0.7, max_tokens: int = 1000) -> dict:
    """Send a prompt to the Groq LLM and return the parsed JSON response.

    Args:
        prompt:      The user message to send.
        temperature: Sampling temperature (lower = more consistent).
        max_tokens:  Maximum tokens in the reply.

    Returns:
        Parsed dict from the LLM response.

    Raises:
        HTTPException 502 if the LLM call fails or returns invalid JSON.
    """
    try:
        response = _get_client().chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as exc:
        logger.exception("LLM returned invalid JSON")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI returned an unreadable response.") from exc
    except Exception as exc:
        logger.exception("LLM request failed")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"AI request failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class JobInput(BaseModel):
    """Request body for generating interview questions."""

    job_description: str = Field(..., min_length=50, description="The full job description text.")


class AnswerInput(BaseModel):
    """Request body for evaluating a single interview answer."""

    question: str = Field(..., description="The interview question that was asked.")
    answer: str = Field(..., min_length=10, description="The candidate's answer.")
    job_description: str = Field(..., description="Original job description for context.")
    question_number: Annotated[int, Field(ge=1, le=QUESTION_COUNT)] = Field(
        ..., description=f"Question number (1-{QUESTION_COUNT})."
    )


class QAPair(BaseModel):
    """A single question-answer pair with its score, used in the final report."""

    question: str
    answer: str
    score: int = Field(..., ge=0, le=10)


class ReportInput(BaseModel):
    """Request body for generating the final interview performance report."""

    job_description: str = Field(..., description="Original job description for context.")
    qa_pairs: list[QAPair] = Field(..., description="All question-answer pairs with scores.")


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Serve the main page where the user pastes the job description."""
    return templates.TemplateResponse(request=request, name="index.html")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.post("/generate-questions")
async def generate_questions(data: JobInput) -> JSONResponse:
    """Generate exactly 6 tailored interview questions from a job description.

    The question set always includes 2 behavioural, 2 technical, 1 situational,
    and 1 motivation question, all specific to the provided job description.

    Args:
        data: The job description text.

    Returns:
        JSON with keys: role_title, company_hint, questions (list of 6).

    Raises:
        HTTP 502 if the LLM call fails.
    """
    logger.info("Generating questions (JD length: %d chars)", len(data.job_description))

    prompt = f"""You are an expert technical interviewer. Analyse this job description and generate exactly {QUESTION_COUNT} interview questions.

Job Description:
{data.job_description}

Create a mix of:
- 2 behavioral questions (about past experience, teamwork, challenges)
- 2 technical questions (specific to the role's tech stack and skills)
- 1 situational question (how would you handle X scenario)
- 1 motivation question (why this role, career goals)

Return ONLY a valid JSON object:
{{
  "role_title": "inferred job title from the description",
  "company_hint": "company name if mentioned, otherwise 'this company'",
  "questions": [
    {{
      "number": 1,
      "type": "Behavioral",
      "question": "Tell me about a time when..."
    }}
  ]
}}

Make the questions specific to the actual job description, not generic."""

    result = _llm(prompt, temperature=0.7)
    logger.info("Questions generated for role: %r", result.get("role_title", "unknown"))
    return JSONResponse(content=result)


@app.post("/evaluate-answer")
async def evaluate_answer(data: AnswerInput) -> JSONResponse:
    """Score a single interview answer and return coaching feedback.

    Evaluates relevance, depth, clarity, and professionalism on a 1-10 scale.
    Score labels: 1-3 = Weak, 4-6 = Average, 7-8 = Strong, 9-10 = Excellent.

    Args:
        data: The question, the candidate's answer, job context, and question number.

    Returns:
        JSON with: score, score_label, what_was_good, what_to_improve, pro_tip.

    Raises:
        HTTP 502 if the LLM call fails.
    """
    logger.info(
        "Evaluating answer for question %d/%d (answer length: %d chars)",
        data.question_number, QUESTION_COUNT, len(data.answer),
    )

    prompt = f"""You are an expert interviewer evaluating a candidate's answer.

Job context: {data.job_description[:500]}
Question ({data.question_number}/{QUESTION_COUNT}): {data.question}
Candidate's answer: {data.answer}

Evaluate this answer strictly but fairly. Consider: relevance, depth, clarity, and professionalism.

Return ONLY a valid JSON object:
{{
  "score": 8,
  "score_label": "Strong",
  "what_was_good": "One specific thing done well in 1-2 sentences",
  "what_to_improve": "One specific improvement in 1-2 sentences",
  "pro_tip": "One actionable tip to make this answer even better"
}}

Score guide: 1-3 = Weak, 4-6 = Average, 7-8 = Strong, 9-10 = Excellent
Be honest -- not every answer deserves a high score."""

    result = _llm(prompt, temperature=0.5)
    logger.info("Answer scored: %s/10 (%s)", result.get("score", "?"), result.get("score_label", "?"))
    return JSONResponse(content=result)


@app.post("/generate-report")
async def generate_report(data: ReportInput) -> JSONResponse:
    """Generate a full performance report summarising the entire interview.

    Analyses all question-answer pairs together to identify strengths,
    weaknesses, and a concrete action plan for the real interview.

    Args:
        data: The job description and all QA pairs with their scores.

    Returns:
        JSON with: overall_score, overall_label, summary, top_strengths,
        top_weaknesses, action_plan, hire_likelihood, closing_advice.

    Raises:
        HTTP 502 if the LLM call fails.
    """
    if not data.qa_pairs:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No answers provided for the report.")

    logger.info("Generating final report (%d QA pairs)", len(data.qa_pairs))

    qa_text = "\n\n".join([
        f"Q{i + 1}: {qa.question}\nAnswer: {qa.answer}\nScore: {qa.score}/10"
        for i, qa in enumerate(data.qa_pairs)
    ])

    prompt = f"""You are an expert career coach. Review this full mock interview and write a final report.

Job: {data.job_description[:400]}

Interview transcript:
{qa_text}

Return ONLY a valid JSON object:
{{
  "overall_score": 7,
  "overall_label": "Good Performance",
  "summary": "2-3 sentence overall assessment of the candidate's performance",
  "top_strengths": [
    "Specific strength observed across answers",
    "Another strength"
  ],
  "top_weaknesses": [
    "Specific area to improve",
    "Another weakness"
  ],
  "action_plan": [
    "Concrete thing to practice before the real interview",
    "Another action item",
    "A third action item"
  ],
  "hire_likelihood": "Strong Maybe",
  "closing_advice": "One motivating sentence of advice"
}}

hire_likelihood options: "Unlikely", "Possible", "Strong Maybe", "Likely", "Very Likely" """

    result = _llm(prompt, temperature=0.6)
    logger.info(
        "Report generated: overall=%s/10 likelihood=%r",
        result.get("overall_score", "?"),
        result.get("hire_likelihood", "?"),
    )
    return JSONResponse(content=result)


# ---------------------------------------------------------------------------
# Local dev runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
