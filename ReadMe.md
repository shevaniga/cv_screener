AI\_CV\_SCREENER



\# AI Resume Screening \& Ranking System



A Python-based AI resume screening system for an SDE Intern role.



The system reads a folder of PDF resumes, extracts candidate information and resume evidence, applies hard eligibility rules for Python and meaningful AI/LLM/agentic experience, scores eligible candidates out of 100, enriches GitHub information when available, and generates a ranked `results.json`.



\## Features



\- PDF resume ingestion

\- Candidate name, email and GitHub extraction

\- Duplicate resume detection

\- Hard eligibility filtering

\- Python and backend skill matching

\- AI/LLM/RAG/agentic project analysis

\- Explainable scoring out of 100

\- Thin LLM/API wrapper penalty

\- Tutorial/detail-free project penalty

\- Classical ML scoring cap

\- Optional Gemini LLM review

\- Optional GitHub public activity enrichment

\- Graceful handling of malformed resumes and API failures

\- JSON output with ranked candidates and rejection reasons

\- Automated test suite



\## Project Structure



&#x20;   cv\_screener/

&#x20;   ├── main.py

&#x20;   ├── requirements.txt

&#x20;   ├── README.md

&#x20;   ├── .env.example

&#x20;   ├── .env.local

&#x20;   ├── src/

&#x20;   │   ├── config.py

&#x20;   │   ├── ingest.py

&#x20;   │   ├── extract.py

&#x20;   │   ├── matching.py

&#x20;   │   ├── eligibility.py

&#x20;   │   ├── scoring.py

&#x20;   │   ├── github.py

&#x20;   │   ├── llm.py

&#x20;   │   ├── models.py

&#x20;   │   └── pipeline.py

&#x20;   ├── tests/

&#x20;   ├── resumes\_dataset/

&#x20;   └── output/

&#x20;       └── results.json



\## Setup



Create and activate a virtual environment:



&#x20;   python -m venv .venv



Windows PowerShell:



&#x20;   .\\.venv\\Scripts\\Activate.ps1



Install dependencies:



&#x20;   pip install -r requirements.txt



\## Environment Configuration



Create `.env.local` in the project root.



&#x20;   LLM\_API\_KEY=your\_gemini\_api\_key

&#x20;   LLM\_MODEL=your\_current\_gemini\_model

&#x20;   GITHUB\_TOKEN=optional\_github\_token



API keys are loaded from the environment and are not committed to the repository.



The GitHub token is optional. Without it, GitHub enrichment still runs using unauthenticated public API access and may be affected by the lower API rate limit.



\## Run



Run the complete pipeline:



&#x20;   python main.py --input ./resumes\_dataset --output ./output/results.json



Run completely offline without GitHub or LLM enrichment:



&#x20;   python main.py --input ./resumes\_dataset --output ./output/results.json --no-github --no-llm



Run the test suite:



&#x20;   python -m pytest -q



\## Output



The generated `output/results.json` contains:



\- batch summary

\- ranked eligible candidates

\- candidate score and score breakdown

\- matched skills

\- resume evidence

\- strengths

\- concerns

\- GitHub status and summary

\- LLM status

\- rejected candidates with explicit reasons

\- failed resumes

\- duplicate resumes skipped



The scoring output is designed to be explainable: candidate scores are accompanied by evidence and reasons rather than being presented as unexplained numbers.



\## Eligibility



Eligibility is determined using deterministic rules before ranking.



A candidate must show:



1\. Genuine Python evidence in a project, experience or relevant skill context.

2\. Meaningful AI/LLM/RAG/agentic evidence in a project or experience context.



Python alone does not make a candidate eligible.



AI claims that only appear as vague statements or framework names in a skills list are not treated as sufficient project evidence.



Classical machine learning can satisfy the configured eligibility rule, but its AI-depth contribution is capped so that a traditional ML project does not receive the same AI-depth score as a demonstrated LLM, RAG or agentic system.



\## Scoring



The scoring model follows the assignment's 100-point structure:



| Category | Weight |

|---|---:|

| AI / Agentic / RAG | 40 |

| Python \& Backend | 30 |

| Cloud / Deployment / Full Stack | 15 |

| GitHub | 10 |

| Engineering Depth | 5 |

| \*\*Total\*\* | \*\*100\*\* |



Project and work experience evidence receives more weight than skills-list-only mentions.



Additional scoring rules include:



\- thin LLM/API wrappers are penalized

\- tutorial-style or detail-free projects are penalized

\- classical ML AI depth is capped

\- candidates without strong LLM/RAG/agentic evidence have a total-score ceiling

\- every score is accompanied by evidence or an explanation



\## LLM Usage



Gemini is an optional scoring-assistance layer implemented in `src/llm.py`.



The LLM:



\- receives project and experience text rather than candidate identity fields

\- returns structured JSON

\- uses Pydantic validation

\- must provide an evidence quote from the resume

\- cannot determine eligibility

\- can adjust the rule-based AI-depth score only within a bounded range

\- falls back to the deterministic rule-based score if the API fails



This keeps the main screening logic predictable and testable while allowing an LLM to provide additional project-depth judgement.



\## GitHub Enrichment



When a candidate has a GitHub profile, the system can query public GitHub data and add a bounded GitHub signal to the score.



The GitHub component considers:



\- recent public activity

\- maintained public repositories

\- repository relevance to Python, AI and software engineering



GitHub enrichment is not an eligibility requirement.



Missing profiles, API failures and rate limits are handled without failing the resume-processing batch.



Results are cached during a run and GitHub requests use bounded concurrency.



\## Reliability



The pipeline is designed so that one problematic resume or external API failure does not terminate the complete batch.



Handled cases include:



\- malformed PDFs

\- unreadable resumes

\- duplicate files

\- missing GitHub profiles

\- GitHub API failures

\- GitHub rate limits

\- LLM API failures

\- missing API credentials



\## Testing



The project includes unit tests covering extraction, eligibility, matching, scoring and failure-handling behavior.



Run:



&#x20;   python -m pytest -q



Current test status:



&#x20;   41 passed



\## Design Decisions



\### Deterministic eligibility



Eligibility is kept separate from the LLM so that an LLM cannot make an otherwise ineligible resume eligible.



\### Evidence-based scoring



Scores are derived from detected resume evidence and are accompanied by evidence snippets, strengths and concerns.



\### Bounded LLM influence



The LLM is used as a controlled scoring-assistance layer rather than as the sole ranking mechanism.



\### Graceful external failures



GitHub and LLM failures do not stop the batch. The system records the status and continues using the available deterministic information.



\### No frontend or database



The assignment can be fulfilled through a CLI pipeline, so unnecessary frontend, authentication and database infrastructure was intentionally avoided.



\## If I Had More Time



1\. Calibrate keyword lists and scoring weights against a larger human-labelled resume set and measure precision and recall.

2\. Add OCR support for scanned PDFs.

3\. Add DOCX and TXT ingestion.

4\. Use the LLM as a human-review flag for borderline cases while keeping eligibility deterministic.

5\. Persist GitHub and LLM caches between runs.

6\. Add an optional FastAPI interface.

7\. Expand the test set with more adversarial resume formats and terminology.

