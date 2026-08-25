# SentinelRisk — Project Directory Structure & Codebase Map

```
SentinelRisk/
├── backend/
│   ├── app/
│   │   ├── api/                      # REST Endpoints
│   │   │   ├── cases.py              # Review queue & case management API
│   │   │   ├── dataset.py            # Dataset status API
│   │   │   ├── health.py             # Liveness, readiness, & dependency health probes
│   │   │   ├── incidents.py          # Incident simulation & scenario API
│   │   │   ├── metrics.py            # Operational observability & metrics API
│   │   │   ├── placeholders.py       # Future endpoint stubs (/events, /model)
│   │   │   └── risk.py               # Real-time risk scoring API (POST /risk/evaluate)
│   │   ├── db/                       # Database ORM & Connection
│   │   │   ├── database.py           # SQLite connection & session management
│   │   │   └── models.py             # 9 Foundation ORM models
│   │   ├── graph/                    # Entity Graph Intelligence Layer
│   │   │   ├── entity_graph.py       # Heterogeneous NetworkX graph constructor
│   │   │   └── ring_detector.py      # Point-in-time syndicate ring detector
│   │   ├── investigation/            # AI Investigation Agent Layer
│   │   │   ├── agent.py              # Evidence-grounded InvestigationAgent
│   │   │   ├── case_manager.py       # Review queue & case lifecycle manager
│   │   │   ├── context_builder.py    # Fact & entity context assembler
│   │   │   ├── models.py             # Pydantic schemas (EvidenceItem, Finding, Report)
│   │   │   └── providers.py          # Decoupled MockInvestigationLLM & Gemini LLM
│   │   ├── policy/                   # Deterministic Policy Engine Layer
│   │   │   ├── engine.py             # Precedence hierarchy & tri-state evaluator
│   │   │   ├── models.py             # Policy decision records & explanations
│   │   │   └── rules.py              # 6 Deterministic velocity & anomaly rules
│   │   ├── scoring/                  # Real-Time Scoring & Production Readiness
│   │   │   ├── idempotency.py        # Canonical hashing & duplicate conflict cache
│   │   │   ├── load_tester.py        # In-process latency profiler & load tester
│   │   │   ├── metrics.py            # Correlation IDs, latency percentiles, alerts
│   │   │   ├── realtime_service.py   # Multi-signal real-time scoring orchestrator
│   │   │   ├── resilience.py         # Dependency health & graceful degradation fallbacks
│   │   │   └── validation.py         # Request payload validator & SHA-256 digest
│   │   ├── config.py                 # Pydantic settings & environment configuration
│   │   └── main.py                   # FastAPI application factory & lifespan
│   └── requirements.txt              # Backend dependencies
│
├── frontend/                         # Next.js 14 App Router Console
│   ├── src/
│   │   ├── app/
│   │   │   ├── incidents/page.tsx    # "What Broke at 2 AM" Incident Simulator UI
│   │   │   ├── live-feed/page.tsx    # Live Transaction Feed UI
│   │   │   ├── model-evaluation/page.tsx # Model Benchmark & ROC/PR Curves UI
│   │   │   ├── operations/page.tsx   # Operational Metrics & Health Console UI
│   │   │   ├── review-queue/page.tsx # Analyst Review Queue & Case Investigation UI
│   │   │   ├── layout.tsx            # Global dashboard layout
│   │   │   └── page.tsx              # Risk Overview executive dashboard
│   │   └── components/               # Reusable UI components (Sidebar, Header, Cards)
│   └── package.json                  # Frontend dependencies
│
├── ml/                               # Machine Learning Baselines & Artifacts
│   ├── features/                     # Feature extraction & pipeline
│   │   ├── pipeline.py               # Point-in-time stateful feature pipeline
│   │   └── verifier.py               # Zero-leakage verification suite
│   ├── models/                       # Trained binary models
│   │   ├── lightgbm_model.pkl        # LightGBM classifier artifact
│   │   └── logistic_regression.pkl   # Logistic Regression baseline artifact
│   └── training/                     # Training & evaluation scripts
│
├── simulation/                       # Synthetic Payments & Incident Generators
│   ├── data_generation/              # 6-Month payments ecosystem generator
│   └── incident_simulator/           # 2 AM Attack scenarios & simulator
│       ├── scenarios.py              # Attack profiles (Card Testing, ATO, Ring)
│       └── simulator.py              # Attack replay & containment engine
│
├── evaluation/                       # Audit Records & Benchmark Artifacts
│   ├── final/                        # Authoritative Stage 10 audit files
│   │   ├── archetype-performance.csv
│   │   ├── final-benchmark.csv
│   │   ├── metric-audit.csv
│   │   └── stage_acceptance.json
│   ├── graph_detection/              # Stage 6 evaluation artifacts
│   ├── investigation/                # Stage 8 evaluation artifacts
│   ├── ml_baselines/                 # Stage 5 evaluation artifacts
│   ├── policy_v1/                    # Stage 7 decision records & policy audit
│   ├── production/                   # Stage 9 load test & latency reports
│   └── rules_baseline/               # Stage 4 baseline evaluation artifacts
│
├── config/                           # Declarative Configurations
│   └── policy.yaml                   # sentinelrisk-policy-v1 configuration
│
├── docs/                             # Architecture & Submission Documentation
│   ├── architecture.md               # System architecture & design decisions
│   ├── benchmark-methodology.md      # Honest measurement & window definitions
│   ├── business-impact.md            # Cost-sensitive tradeoff analysis
│   ├── demo-script.md                # 5-7 minute timed panel demo script
│   ├── final-audit.md                # System-wide audit report
│   ├── final-completion-report.md    # Authoritative 24-section completion report
│   ├── panel-defense.md              # Top 25 Razorpay panel technical answers
│   ├── production-architecture.md    # Real-time request flow & cloud scaling
│   ├── project-structure.md          # Audited directory tree map
│   ├── reproduction.md               # Clean bootstrap & setup guide
│   └── two-minute-pitch.md           # Spoken 2-minute elevator pitch
│
├── scripts/                          # Utility & Demo CLI Scripts
│   ├── demo.py                       # Unified scenario demo runner
│   ├── evaluate_graph.py             # Graph ring detection evaluator
│   ├── evaluate_investigations.py    # LLM investigation quality benchmark
│   ├── generate_data.py              # Synthetic world generator
│   ├── generate_features.py          # Point-in-time feature generator
│   ├── load_test.py                  # In-process latency profiler
│   ├── replay_policy.py              # Offline policy replay evaluator
│   ├── replay_risk.py                # Decision reproducibility verifier
│   ├── run_demo.py                   # Interactive demo launcher
│   ├── setup_demo.py                 # Single-command environment bootstrap
│   └── simulate_incident.py          # 2 AM incident simulator CLI
│
├── tests/                            # Comprehensive Automated Test Suite
│   ├── unit/                         # Unit tests (102 tests)
│   ├── integration/                  # API integration tests
│   └── test_end_to_end.py            # End-to-end integration & immutability tests (6 tests)
│
└── README.md                         # Final submission overview & documentation
```
