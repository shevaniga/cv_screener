# AI Resume Screening & Ranking System

A Python-based resume screening system for an SDE Intern role.

The system processes resumes, checks eligibility, scores candidates, enriches GitHub information when available, and generates a ranked `results.json`.

## Features

* PDF resume parsing
* Candidate information extraction
* Python + AI/LLM eligibility filtering
* Project and skill matching
* Explainable scoring
* GitHub enrichment
* Optional Gemini LLM review
* Duplicate and invalid resume handling
* JSON output
* Automated tests

## Project Structure

```text
cv_screener/
├── main.py
├── requirements.txt
├── README.md
├── .env.example
├── src/
│   ├── config.py
│   ├── ingest.py
│   ├── extract.py
│   ├── matching.py
│   ├── eligibility.py
│   ├── scoring.py
│   ├── github.py
│   ├── llm.py
│   ├── models.py
│   └── pipeline.py
├── tests/
├── resumes_dataset/
└── output/
    └── results.json
```

## Setup

```bash
python -m venv .venv
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Environment

Create `.env.local`:

```text
LLM_API_KEY=your_api_key
LLM_MODEL=your_model
GITHUB_TOKEN=optional
```

Do not commit `.env.local` or API keys.

## Run

```bash
python main.py --input ./resumes_dataset --output ./output/results.json
```

Run tests:

```bash
python -m pytest -q
```

## Eligibility

A candidate must have:

* Genuine Python experience
* Meaningful AI/LLM/RAG/agentic experience

Skills listed without supporting project or experience evidence are not treated as sufficient.

## Scoring

| Category                        |  Weight |
| ------------------------------- | ------: |
| AI / Agentic / RAG              |      40 |
| Python & Backend                |      30 |
| Cloud / Deployment / Full Stack |      15 |
| GitHub                          |      10 |
| Engineering Depth               |       5 |
| **Total**                       | **100** |

## Output

Results are saved to:

```text
output/results.json
```

The output includes ranked candidates, eligibility, score breakdown, matched skills, evidence, project summary, GitHub status, LLM status, and rejection reasons.

## LLM & GitHub

Gemini is used as an optional scoring-assistance layer for AI project depth.

GitHub enrichment checks public activity and relevant repositories when a profile is available.

Both services fail gracefully without stopping the resume-processing batch.

## Testing

```text
41 passed
```
