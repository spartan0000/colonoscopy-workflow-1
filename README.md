# Colonoscopy Workflow Automation

A FastAPI-based system that eliminates repetitive manual work from colonoscopy reporting. It combines an LLM-powered transcription layer (in progress) with a deterministic, rules-based triage engine to automate two of the most time-consuming tasks in endoscopy: **data entry** and **post-procedure follow-up decisions**.

---

## The Problem

After every colonoscopy, an endoscopist must:

1. **Transcribe findings** — re-enter structured data (polyp count, size, location, histology, prep scores, etc.) into a system that already has a free-text report. This is pure repetition.
2. **Determine follow-up** — apply surveillance guidelines to decide whether a patient needs a 3-, 5-, or 10-year follow-up, immediate re-scope, or discharge. The guidelines are well-defined and algorithmic, yet this decision is currently made manually each time.
3. **Calculate KPIs** — endoscopists are required to track metrics like adenoma detection rate (ADR), cecal intubation rate (CIR), and withdrawal time. These currently require complex database queries and manual spreadsheet work.

Neither of the first two tasks benefits meaningfully from human judgment. Both are error-prone and time-consuming at scale.

---

## Solution Overview

```mermaid
flowchart TD
    A[Free-text colonoscopy report] --> B[LLM Transcription Layer\nAzure OpenAI]
    B --> C[Structured JSON\nColonoscopySummary]
    C --> D[Data Normalisation\nPolyp stats, age, indication]
    D --> E{Deterministic\nTriage Engine\n24 rules}
    E -->|Immediate review| F[Follow-up: Review Required]
    E -->|3 years| G[Follow-up: 3 Years]
    E -->|5 years| H[Follow-up: 5 Years]
    E -->|10 years| I[Follow-up: 10 Years]
    E -->|Discharge| J[Discharge]
    F & G & H & I & J --> K[(PostgreSQL\nAudit Log)]
    K --> L[KPI Dashboard\nADR · CIR · Withdrawal Time]
```

---

## Why a Deterministic Rules Engine?

The triage engine deliberately does **not** use an LLM to make clinical decisions. LLMs can hallucinate. In medical decision-making, a hallucinated follow-up interval is not an acceptable failure mode.

The rules engine applies the same logic every time, is fully auditable, and produces a named rule alongside every decision — so a clinician can always see exactly why a recommendation was made.

| Layer | Uses LLM? | Reason |
|---|---|---|
| Transcription (parsing free text → JSON) | Yes | Unstructured text extraction; errors are caught by schema validation |
| Triage (follow-up decision) | **No** | Deterministic by design; hallucinations are clinically unacceptable |

---

## System Architecture

```mermaid
flowchart LR
    subgraph API["REST API (FastAPI)"]
        EP["POST /triage"]
    end

    subgraph Services["Services"]
        TS["triage_services.py\nOrchestration"]
        FQ["format_query_json()\nLLM extraction"]
        ND["normalize_data()\nData normalisation"]
        TR["triage()\nRules engine"]
        AO["triage_with_age_out()\nAge-out logic"]
    end

    subgraph LLM["Azure OpenAI"]
        GPT["gpt-4o-mini\nStructured output"]
        WH["Whisper\nAudio transcription\n(planned)"]
    end

    subgraph DB["PostgreSQL"]
        PT[Patient]
        PR[Procedure]
        FN[Finding]
        HI[Histology]
        TG[Triage]
    end

    EP --> TS
    TS --> FQ --> GPT
    TS --> ND --> TR --> AO
    TS --> DB
```

---

## Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI /triage
    participant LLM as Azure OpenAI
    participant Engine as Rules Engine
    participant DB as PostgreSQL

    Client->>API: POST /triage {report_text}
    API->>LLM: Free-text colonoscopy report
    LLM-->>API: ColonoscopySummary (structured JSON)
    API->>Engine: normalize_data()
    Note over Engine: Extracts polyp counts,<br/>sizes, flags, patient age
    Engine->>Engine: Apply rules 1–24 in sequence
    Engine-->>API: {follow_up, rule, reason}
    API->>DB: Write triage record
    API-->>Client: {normalized_data, recommendation}
```

---

## Triage Rules

All 24 rules are applied in priority order. The first matching rule wins.

### Immediate Review Required (`follow_up: 0`)

| Rule | Condition |
|---|---|
| rule_1 | Cecum not reached |
| rule_2 | Inadequate bowel prep (Boston Bowel Prep Score < 6 total, or < 2 in any segment) |
| rule_3 | Serrated polyposis syndrome indication |
| rule_4 | ≥ 10 adenomas |
| rule_21 | Incomplete resection or incomplete retrieval |
| rule_22 | IBD indication |
| rule_24 | Biopsies taken (reason must be reviewed) |

### 3-Year Surveillance

| Rule | Condition |
|---|---|
| rule_5 | Sessile serrated lesion (SSL) ≥ 10 mm |
| rule_6 | SSL with dysplasia |
| rule_7 | Adenoma ≥ 10 mm |
| rule_8 | Tubulovillous or villous adenoma |
| rule_9 | Adenoma with high-grade dysplasia (HGD) |
| rule_10 | ≥ 5 SSLs, all < 10 mm, no other polyps |
| rule_11 | 5–9 adenomas, no high-risk features, no SSL |
| rule_12 | 5–9 combined adenomas and SSLs |
| rule_13 | Hyperplastic polyp ≥ 10 mm |

### 5-Year Surveillance

| Rule | Condition |
|---|---|
| rule_14 | 3–4 adenomas, no SSL, no high-risk features |
| rule_15 | 1–4 SSLs < 10 mm, no dysplasia, no other polyps |
| rule_16 | Adenoma + SSL < 5 total, no high-risk features |

### 10-Year Surveillance

| Rule | Condition |
|---|---|
| rule_17 | 1–2 adenomas < 10 mm, no HGD |
| rule_18 | No polyps |

### Discharge

| Rule | Condition |
|---|---|
| rule_23 | No polyps + Category 1 or 2 family history |
| rule_20 | Patient age + follow-up interval > 75 years (age-out) |

> High-risk polyp rules (rule_5–rule_9) allow surveillance up to age 78 before age-out applies.

---

## KPI Tracking (Planned)

All procedure data is persisted to PostgreSQL, enabling endoscopist-level KPI reporting without manual queries or spreadsheets.

| KPI | Definition | Source fields |
|---|---|---|
| **Adenoma Detection Rate (ADR)** | % of procedures where ≥ 1 adenoma found | `Finding.polyp`, histology classification |
| **Cecal Intubation Rate (CIR)** | % of procedures where cecum was reached | `Procedure.cecum_reached` |
| **Withdrawal Time** | Mean scope withdrawal time in minutes | `Procedure.withdrawal_time` |

---

## Database Schema

```mermaid
erDiagram
    Patient {
        uuid patient_id PK
        string nhi
        string first_name
        string last_name
        date dob
    }
    Procedure {
        uuid procedure_id PK
        uuid patient_id FK
        date procedure_date
        int observed_age
        string endoscopist
        bool cecum_reached
        int bbps_total
        int bbps_right
        int bbps_transverse
        int bbps_left
        string indication
        float withdrawal_time
    }
    Finding {
        uuid finding_id PK
        uuid procedure_id FK
        string finding_type
        string location
        int size_mm
        bool polyp
        bool biopsied
        string resection_method
    }
    Histology {
        uuid histology_id PK
        uuid procedure_id FK
        string location
        int size_mm
        string histology
        bool dysplasia
        string dysplasia_grade
    }
    Triage {
        uuid triage_id PK
        uuid procedure_id FK
        text raw_histology_text
        json histology_json
        json triage_decision
        datetime triage_date_time
    }

    Patient ||--o{ Procedure : ""
    Procedure ||--o{ Finding : ""
    Procedure ||--o{ Histology : ""
    Procedure ||--|| Triage : ""
```

---

## Project Structure

```
colonoscopy-workflow-1/
├── app/
│   ├── api/
│   │   └── triage_route.py          # POST /triage endpoint
│   ├── clients/
│   │   └── llm_clients.py           # Azure OpenAI client configuration
│   ├── db/
│   │   ├── session.py               # SQLAlchemy session management
│   │   ├── init_db.py               # Schema initialisation
│   │   └── models/
│   │       └── colonoscopy_models.py  # ORM models
│   └── services/
│       ├── triage_services.py       # Main orchestration + rules engine
│       └── triage/
│           ├── colonoscopy_triage_model.py  # Pydantic schemas
│           └── extract_json.yaml            # LLM system prompt + schema spec
├── tests/
│   ├── conftest.py                  # Pytest fixtures
│   ├── test_triage_service.py       # Unit tests for all 24 rules
│   ├── test_api_triage.py           # Integration tests for /triage
│   └── test_db.py                   # Database write tests
├── docker-compose.yml               # PostgreSQL container
└── pyproject.toml
```

---

## Setup

### Prerequisites

- Python 3.13+
- Docker (for PostgreSQL)
- [`uv`](https://github.com/astral-sh/uv) (recommended) or pip

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd colonoscopy-workflow-1
uv sync
```

### 2. Configure environment

Create a `.env` file in the project root with the following variables:

```env
DATABASE_URL=postgresql://practice_user:practice_password@localhost:5432/practice_db
TEST_DATABASE_URL=postgresql://practice_user:practice_password@localhost:5432/test_db

# Azure OpenAI (transcription + JSON extraction)
AZURE_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_GPT_API_VERSION=...

# Optional: additional Azure deployments
AZURE_EMBEDDING_API_VERSION=...
HNZ_ENDPOINT=...
HNZ_API_KEY=...
HNZ_API_VERSION=...
AZURE_TRANSCRIBE_ENDPOINT=...
AZURE_TRANSCRIBE_API_VERSION=...
AZURE_WHISPER_ENDPOINT=...
AZURE_WHISPER_API_VERSION=...
```

### 3. Start the database

```bash
docker compose up -d
```

### 4. Run the API

```bash
uv run fastapi dev app/main.py
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 5. Run tests

```bash
# Unit tests only (no external dependencies required)
uv run pytest tests/ -m "not integration"

# All tests including integration (requires Azure OpenAI credentials)
uv run pytest tests/
```

---

## API Reference

### `POST /triage`

Submit a free-text colonoscopy report for automated triage.

**Request**

```json
{
  "report_text": "Patient: John Smith, DOB 1955-03-12 ...\nFindings: 3mm tubular adenoma in ascending colon ..."
}
```

**Response**

```json
{
  "normalized_data": {
    "patient_age": 69,
    "indication": "screening",
    "n_adenoma": 1,
    "max_adenoma": 3,
    "hgd_adenoma": false,
    "tva": false,
    "n_ssl": 0,
    "n_hyperplastic": 0,
    "cecum_reached": true,
    "bbps_total": 7
  },
  "recommendation": {
    "follow_up": 10,
    "rule": "rule_17",
    "reason": "1-2 adenomas less than 10mm with no high grade dysplasia"
  }
}
```

`follow_up` values:
- `0` — requires human review
- `3`, `5`, `10` — years until next colonoscopy
- `20` — discharge (no further surveillance)

---

## Roadmap

- [x] Deterministic triage rules engine (24 rules)
- [x] LLM-powered JSON extraction from free-text reports
- [x] Full audit logging to PostgreSQL
- [x] Unit tests for all triage rules
- [ ] Transcription module (audio → report text via Whisper)
- [ ] KPI dashboard (ADR, CIR, withdrawal time)
- [ ] Patient-facing follow-up letter generation
- [ ] Integration with existing endoscopy reporting systems

---

## Design Principles

- **Determinism over flexibility in clinical logic** — every triage decision maps to an explicit, named rule. No LLM is involved in the follow-up recommendation.
- **Full auditability** — every input and output is written to the database with a timestamp. Nothing is transient.
- **Schema validation as a safety net** — the LLM output is parsed against a strict Pydantic schema before any clinical logic runs. Malformed or ambiguous output is rejected before it reaches the rules engine.
