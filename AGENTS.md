# Repository Guidelines

## Project Structure & Module Organization
This repository is a document workspace for inventory exports and analysis reports. Current structure:
- `PSEG/` contains source inventory exports, organized by site (e.g., `PSEG/NHQ/`).
- `inventory_report.md`, `inventory_deep_report.md`, and `inventory_financial_report.md` are generated analysis summaries.
- `agents.md` describes the Inventory Folder Steward behavior.

If new data sets are added, create a top-level folder per client or site and keep raw files in their original format.

## Build, Test, and Development Commands
There is no build system or test suite configured. Use ad‑hoc analysis scripts when needed and keep any generated outputs in the repository root or under a dedicated `output/` folder.

Example inspection commands:
- `rg --files` to list available files
- `rg \"\\.xlsx$\"` to find Excel exports

Automation:
- `python3 scripts/inventory_watch.py` runs a watch loop on `inbox/`, auto-detects sites, renames/sorts, dedupes, and regenerates `inventory_audit_report.html`.

## Coding Style & Naming Conventions
When adding scripts or reports:
- Use 2‑space or 4‑space indentation consistently within a file.
- Prefer ASCII text and simple Markdown formatting.
- Use descriptive filenames like `inventory_financial_report.md`.

For inventory files, prefer descriptive naming:
- `YYYY-MM-DD_site_doc_type_source_descriptor.xlsx`
- Example: `2025-12-23_pseg_nhq_exports_compass_gl.xlsx`

## Testing Guidelines
No automated tests are present. If you add scripts, include a short “How to run” note at the top or in a nearby README.

## Commit & Pull Request Guidelines
This repository is not initialized as a Git repository, so no commit or PR conventions are available. If Git is later enabled, add a short section here describing commit message style and PR expectations.

## Security & Configuration Tips
Do not store secrets or credentials in this repo. If any configuration is required, place it in a local, ignored file (e.g., `.env`) and document the expected keys in a README.
