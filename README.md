# LexAI Paper Submission Repository

This repository is prepared for paper artifact submission and review of LexAI (transition-aware legal QA for Indian law).

## Primary Artifacts

- [paper.md](paper.md): Paper source draft.
- [main.pdf](main.pdf): Paper PDF artifact.
- [backend/evaluation/results/figures](backend/evaluation/results/figures): Figures referenced by the paper.
- [backend/README.md](backend/README.md): Backend setup and execution details.
- [frontend/README.md](frontend/README.md): Frontend setup details.

## Submission-Oriented Structure

- [backend](backend): Core research implementation (API, retrieval, data pipeline, evaluation, tests).
- [frontend](frontend): Demo UI for system interaction.
- [data](data): Datasets and static data artifacts used by the project.
- [start.sh](start.sh): Convenience launcher.

## Pre-Submission Cleanup (Recommended)

The following items are development/runtime artifacts and should be removed from the publication package unless explicitly required by the venue.

### Remove or Exclude

1. Local secrets and machine artifacts
- [backend/.env](backend/.env)
- [backend/.DS_Store](backend/.DS_Store)
- [backend/evaluation/.DS_Store](backend/evaluation/.DS_Store)
- [backend/evaluation/results/.DS_Store](backend/evaluation/results/.DS_Store)

2. Generated vector databases and local state
- [backend/chroma_db](backend/chroma_db)
- [backend/chroma_legal_db](backend/chroma_legal_db)
- [backend/chromadb_data](backend/chromadb_data)
- [backend/data_pipeline/chroma_legal_db](backend/data_pipeline/chroma_legal_db)
- [backend/legal_research_db](backend/legal_research_db)
- [chroma_db](chroma_db)
- [legal_research_db](legal_research_db)

3. Logs, temporary outputs, and backups
- [backend/logs](backend/logs)
- [backend/evaluation/evaluation/logs](backend/evaluation/evaluation/logs)
- [hindi_temp/logs](hindi_temp/logs)
- [data/unanswered_queries.log](data/unanswered_queries.log)
- [backend/data/unanswered_queries.log](backend/data/unanswered_queries.log)
- [backend/evaluation/data/unanswered_queries.log](backend/evaluation/data/unanswered_queries.log)
- [data/backup](data/backup)
- [backend/data/backup](backend/data/backup)
- [backend/data_pipeline/data/backup](backend/data_pipeline/data/backup)

4. Local environment/vendor folders
- [backend/#](backend/#)
- [backend/or](backend/or)
- [backend/python3.10](backend/python3.10)

5. Duplicate paper PDFs
- [main.pdf](main.pdf)
- [LEXAI-2.pdf](LEXAI-2.pdf)

Keep only one canonical final paper PDF in the submission package and archive/remove the other.

## What to Keep for Reviewers

1. Source code needed to reproduce results: [backend](backend), [frontend](frontend)
2. Reproducibility docs: [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md), [backend/REPRODUCIBILITY.md](backend/REPRODUCIBILITY.md)
3. Paper text and figures: [paper.md](paper.md), one final PDF, [backend/evaluation/results/figures](backend/evaluation/results/figures)
4. Dependency manifests: [backend/requirements.txt](backend/requirements.txt), [frontend/package.json](frontend/package.json)

## Final Checklist Before Submission

1. Ensure [backend/.env](backend/.env) is not included in the uploaded artifact.
2. Keep exactly one final paper PDF at repository root.
3. Remove generated databases and logs listed above.
4. Verify setup works from clean state using [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).
5. Confirm all figures referenced in [paper.md](paper.md) are present in [backend/evaluation/results/figures](backend/evaluation/results/figures).
