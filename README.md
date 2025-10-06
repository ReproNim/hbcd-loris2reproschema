# hbcd-loris2reproschema

Convert HBCD (HEALthy Brain and Child Development) LORIS data dictionaries to ReproSchema with an automated, change‑gated GitHub Actions pipeline.

## What This Repo Does
- Converts LORIS CSVs into a three‑layer ReproSchema structure (Protocol → Activities → Items).
- Detects significant changes between CSV versions and only converts when thresholds are met.
- Validates generated schemas and publishes tagged releases after PRs are merged.

## Recommended: Online Workflow (GitHub Actions)
1. Configure secrets: add `HBCD_USERNAME` and `HBCD_PASSWORD` (Repository → Settings → Secrets and variables → Actions).
2. Run “Retrieve HBCD Data Dictionary” (manual or scheduled weekly). It:
   - Downloads latest CSV → compares with previous → decides if conversion is needed.
   - If significant: commits the CSV and dispatches “Automated LORIS to ReproSchema Update”.
3. Automated Update creates a PR with generated schemas, logs, and a report.
4. Merge the PR. After merge, a tag `vYYYY.MM.DD(.N)` is created and a GitHub Release is published.

## Optional: Local Use (Developers)
```bash
# Env (Python 3.10)
micromamba create -n hbcd python=3.10
micromamba activate hbcd
micromamba install -c conda-forge requests pandas pyyaml beautifulsoup4
pip install reproschema pre-commit

# Convert + validate
python scripts/loris2reproschema.py \
  --csv_file loris_data_dictionaries/hbcd_data_dictionary_YYYY-MM-DD.csv \
  --config_file config/conversion.yml \
  --output_path reproschema_output
reproschema validate reproschema_output/HBCD_LORIS/HBCD_LORIS_schema
```

## Repository Structure
```
config/                 # YAML configs (conversion, thresholds, pipeline)
reproschema_output/     # Generated protocol + activities
loris_data_dictionaries/# Downloaded LORIS CSVs
scripts/                # Conversion + automation tools
.github/workflows/      # CI workflows (retrieve, automated update)
logs/, reports/, docs/  # Artifacts, summaries, and comparison data
```

## Configuration
- `config/conversion.yml`: column mappings, type overrides, and protocol settings.
- `config/change_detection.yml`: thresholds and column rules (aligned to CSV headers).
- `config/pipeline.yml`: output paths, validation options, and comparison settings.

## CI Overview
- Orchestrator: `./.github/workflows/automated_update.yml` delegates to two reusable workflows.
  - `reusable-update.yml`: checks out code, runs conversion + validation, opens an auto PR if changes exist, and posts a one‑line schema diff summary (main → HEAD). Attaches `pr-schema-diff` JSON as an artifact.
  - `reusable-release.yml`: waits for that PR to be merged, then tags (`vYYYY.MM.DD(.N)`), creates a GitHub Release, and publishes comparison JSON for recent versions into `docs/data/` (updates `docs/index.html`).
- Composite actions: live under `./.github/actions/` for easy reuse.
  - `setup-python-deps`: sets up Python 3.10 and installs pinned deps.
  - `pr-schema-diff`: generates a JSON diff and emits a concise summary for PRs.
  - `publish-comparisons`: generates/commits website comparison data on main.
- On‑demand comparisons: run any pair without regenerating everything.
  - Action: “Generate On‑Demand Comparison” (workflow_dispatch). Inputs: `from_ref`, `to_ref`, `publish` (false by default).
    - Always uploads the JSON as an artifact; when `publish=true`, it commits `docs/data/<from>_to_<to>.json` so the website can show it.
  - CLI example: `gh workflow run compare_on_demand.yml -f from_ref=v2025.09.15 -f to_ref=v2025.10.05 -f publish=true --ref main`.
- Diff website: `docs/index.html` lists tag versions dynamically and includes an On‑Demand panel.
  - Versions are tags only, loaded from `docs/data/index.json` (published on main) with a GitHub API fallback.
  - Enter refs to preview a published pair; if not found, run the on‑demand Action with `publish=true` to publish `docs/data/<from>_to_<to>.json`.

## Development & Quality
- Pre-commit: `pre-commit install && pre-commit run --all-files` (Black, YAML/JSON checks, optional validation hook).
- Validate schemas: `reproschema validate reproschema_output/HBCD_LORIS/HBCD_LORIS_schema`.
- Data quality checks (non-failing): `python scripts/check_data_quality.py`.

## Notes
- Tags/releases are created only after the auto PR is merged.
- Comparisons are generated as artifacts; they do not block CI.

## License
MIT — see [LICENSE](LICENSE).
