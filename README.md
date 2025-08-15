# hbcd-loris2reproschema

HBCD LORIS format to ReproSchema format converter with automated update capabilities.

## Overview

This repository converts HBCD (HEALthy Brain and Child Development) study data from LORIS format to ReproSchema format. ReproSchema is a standardized format for representing questionnaires and assessments in research studies.

### Features
- ✅ Three-layer ReproSchema structure (Protocol → Activities → Items)
- ✅ Automatic data quality fixes for known issues
- ✅ Semi-automated and fully automated update workflows
- ✅ Built-in validation and quality reporting
- ✅ GitHub Actions integration for scheduled updates

## Quick Start

### Prerequisites
```bash
# Create and activate environment
micromamba create -n hbcd python=3.10
micromamba activate hbcd

# Install dependencies
micromamba install -c conda-forge requests pandas pyyaml beautifulsoup4
pip install reproschema
```

### Manual Conversion
```bash
# 1. Fetch latest data dictionary
python scripts/retrieve_script.py --username $LORIS_USER --password $LORIS_PASS --output_dir loris_data_dictionaries/

# 2. Convert to ReproSchema
python scripts/loris2reproschema.py --csv_file loris_data_dictionaries/hbcd_data_dictionary_YYYY-MM-DD.csv --config_file hbcd-loris.yml --output_path reproschema_output/

# 3. Validate schemas
reproschema validate reproschema_output/HBCD_LORIS/HBCD_LORIS_schema
```

## 🤖 Automated Updates

### Semi-Automated Workflow

Run the automated update pipeline with built-in quality checks:

```bash
# Set credentials
export LORIS_USER=your_username
export LORIS_PASS=your_password

# Run update with quality checks
python scripts/automated_update.py

# Review quality report
cat quality_report_*.json | jq .
```

The pipeline will:
- Retrieve latest LORIS data
- Convert with automatic fixes for known issues
- Validate all generated schemas
- Generate detailed quality reports
- Stop if critical issues are found

### Fully Automated (GitHub Actions)

The repository includes GitHub Actions workflow for weekly automated updates:

1. **Setup**: Add `LORIS_USER` and `LORIS_PASS` as GitHub secrets
2. **Schedule**: Runs weekly on Mondays at 2 AM UTC
3. **Process**: 
   - Fetches latest data dictionary
   - Runs conversion with quality checks
   - Creates PR with changes for review
   - Includes quality report as artifact

### Quality Assurance

The converter automatically fixes common data issues:
- **Typos**: Corrects known spelling errors (e.g., "vaginalintercourse" → "vaginal intercourse")
- **Truncated names**: Fixes incomplete activity names (e.g., "ecPROMIS (" → "ecPROMIS")
- **Redundant prefixes**: Removes duplicated variable prefixes
- **Naming conventions**: Ensures filesystem-safe names with proper underscore usage

Each conversion generates a quality report with:
- Statistics on items processed
- Issues detected and fixed
- Warnings requiring review
- Validation results

For detailed configuration and troubleshooting, see [docs/AUTOMATED_UPDATES.md](docs/AUTOMATED_UPDATES.md).

## Repository Structure

```
├── reproschema_output/      # Generated ReproSchema files
│   ├── HBCD_LORIS/         # Protocol-level schema
│   └── activities/          # Activity-level schemas with items
├── loris_data_dictionaries/ # Source LORIS CSV files
├── scripts/                 # Conversion and automation scripts
│   ├── loris2reproschema.py
│   ├── retrieve_script.py
│   └── automated_update.py
├── notes/                   # Documentation and issue tracking
├── hbcd-loris.yml          # Configuration file
└── update_config.yml       # Automation configuration
```

## Configuration

The `hbcd-loris.yml` file controls the conversion mapping:
- Column mappings from LORIS CSV to ReproSchema properties
- Field type mappings (e.g., "Dropdown" → "select")
- Metadata fields to include
- Domain/instrument grouping settings

## Development

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

### Running Tests
```bash
# Validate all schemas
reproschema validate reproschema_output/HBCD_LORIS/HBCD_LORIS_schema

# Check data quality
python scripts/check_data_quality.py
```

## Known Issues

See [notes/ORIGINAL_DATA_ISSUES.md](notes/ORIGINAL_DATA_ISSUES.md) for documentation of source data quality issues and how the converter handles them.

## Contributing

1. Create a feature branch
2. Make your changes
3. Run validation and quality checks
4. Submit a pull request

## License

[Add license information]

## Contact

[Add contact information]