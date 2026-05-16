# SAFE Tool — Prompt Safety Detection for Indian Financial Services

A web-based tool that analyses corporate prompts before they're submitted to external AI systems. Identifies sensitive data using the SAFE framework, returns structured analysis with regulatory citations, and (planned) produces sanitised rewrites.

**Status:** In active development. Detection working. Rewriter in progress. Sprint 1 in progress.

## Why this exists

Financial analysts at Indian firms paste prompts into ChatGPT/Claude that contain client account information, compensation data, deal information, and other content that creates DPDP Act 2023 and SEBI exposure. SAFE intercepts at the prompt level, identifies sensitive categories with sub-section level regulatory citations, and produces structured detection output.

Target users: Chief Compliance Officers, Chief Risk Officers, and Heads of InfoSec at Indian wealth management firms, investment banks, and asset managers.

## The SAFE Framework

| Letter | Meaning | Application |
|--------|---------|-------------|
| **S** | Strip | Remove sensitive data entirely where it adds no analytical value |
| **A** | Anonymise | Replace identifiers with neutral labels that preserve role or function |
| **F** | Frame with context only | Keep the situational context, drop the specifics |
| **E** | Evaluate | Verify the rewritten prompt still accomplishes the original task |

## Architecture

```
┌─────────────┐       ┌──────────────────────┐       ┌──────────────┐
│  Frontend   │──────▶│  Vercel Serverless   │──────▶│  OpenAI API  │
│  (React)    │       │  Functions (Python)  │       │  (gpt-4.1)   │
│             │◀──────│                      │◀──────│              │
└─────────────┘       └──────────────────────┘       └──────────────┘
                              │
                              ├─ api/analyse.py    (detection)
                              ├─ api/rewrite.py    (sanitisation — WIP)
                              └─ api/_lib/         (shared logic)
```

**Current state:**
- Frontend deployed on Vercel
- Backend is Python serverless functions on Vercel
- Detection uses OpenAI GPT-4.1-mini
- Rewriter is scaffolded but not yet functional (prompt placeholder)

**Planned:**
- Claude as production model (per architecture decision in `docs/PROMPT_DESIGN.md`)
- Cross-provider failover (Claude primary, OpenAI fallback)
- Structured logging and observability (Sprint 1)
- Eval framework with golden test sets (Sprint 1)

## Repository structure

```
.
├── api/                    # Production backend (Vercel serverless)
│   ├── analyse.py          # POST /api/analyse — detection endpoint
│   ├── rewrite.py          # POST /api/rewrite — sanitisation (WIP)
│   ├── health.py           # GET /api/health — health check
│   ├── _lib/
│   │   ├── llm_service.py  # LLM client abstraction
│   │   ├── prompts.py      # Detection system prompt (v1.2)
│   │   └── rewriter_prompts.py  # Rewriter prompts (WIP)
│   └── requirements.txt
├── frontend/               # React + Vite UI
├── docs/
│   ├── PROMPT_DESIGN.md    # SAFE framework, prompt evolution, test results
│   └── SETUP.md            # Developer setup guide
├── eval/                   # Evaluation framework (Sprint 1)
├── system-prompts/         # Future: versioned prompts (Sprint 1+)
├── marketing-assets/       # Test outputs for marketing
├── vercel.json
└── README.md
```

## Local development

See `docs/SETUP.md` for full setup instructions.

Quick start:

```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend (local Vercel dev)
vercel dev
```

Environment variables required (set in `.env.local`):

- `OPENAI_API_KEY` — OpenAI API key
- `LLM_PROVIDER` — Currently `openai` (Claude support planned)

## Sprint progress

Following a structured 12-week sprint plan. Current focus:

- **Sprint 1 (current):** Production hardening — retry logic, structured logging, eval framework
- **Sprint 2:** Regulatory RAG integration (separate repo)
- **Sprint 3:** LangChain ensemble retrieval
- **Sprint 5:** LangGraph multi-step orchestration with RAG
- **Sprint 6:** Cloud deployment with IaC, Langfuse observability
- **Sprint 8:** Red-teaming and adversarial testing

## Author

**Manan Jindal** — Senior Full-Stack Engineer (15 years). Building AI architecture skills focused on Indian financial services. Founder of [Arthada](https://arthada.com).

- Medium: https://medium.com/@manan_jindal
- LinkedIn: https://linkedin.com/in/mananjindal