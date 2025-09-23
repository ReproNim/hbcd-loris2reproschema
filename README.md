# hbcd-loris2reproschema

HBCD LORIS format to ReproSchema format converter with smart automated update capabilities.

## Overview

This repository converts HBCD (HEALthy Brain and Child Development) study data from LORIS format to ReproSchema format. ReproSchema is a standardized format for representing questionnaires and assessments in research studies.

### Features
- ✅ Three-layer ReproSchema structure (Protocol → Activities → Items)
- ✅ **Smart change detection** - only converts when significant changes detected
- ✅ Automatic data quality fixes for known issues
- ✅ **Fully automated pipeline** with intelligent workflows
- ✅ Built-in validation and quality reporting
- ✅ **Auto-tagging and releases** - hands-off version management
- ✅ Error handling with retry logic for reliability

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
python scripts/loris2reproschema.py --csv_file loris_data_dictionaries/hbcd_data_dictionary_YYYY-MM-DD.csv --config_file config/conversion.yml --output_path reproschema_output/

# 3. Validate schemas
reproschema validate reproschema_output/HBCD_LORIS/HBCD_LORIS_schema
```

## 🧠 Smart Automated Pipeline

### Intelligent Change Detection

The pipeline uses smart change detection to avoid unnecessary work:

```bash
# Check if conversion is needed
python scripts/detect_changes.py --old-file data1.csv --new-file data2.csv --quiet
# Returns: true (convert needed) or false (skip conversion)
```

**Configurable thresholds** (in `config/change_detection.yml`):
- Minimum field changes: 3
- Minimum new instruments: 1  
- Change percentage threshold: 1.0%
- Ignores timestamps and metadata

### Two-Stage Automated Workflow

**Stage 1: Data Retrieval + Change Detection**
- Runs weekly (Mondays) or manual trigger
- Fetches latest LORIS data dictionary
- Analyzes changes vs previous version
- Only triggers conversion if thresholds met
- Generates detailed comparison reports

**Stage 2: Conversion + Release** (triggered only when needed)
- Converts LORIS data to ReproSchema format
- Validates all generated schemas
- Creates PR with changes
- Auto-merges when quality checks pass
- **Creates tagged release** with date-based versioning

### Fully Automated (GitHub Actions)

**Setup**: Add `HBCD_USERNAME` and `HBCD_PASSWORD` as GitHub secrets

**Smart Pipeline Flow:**
```
📅 Weekly Schedule → 📥 Fetch Data → 🧠 Smart Analysis → ⚖️ Threshold Check
                                                           ↓ (if significant changes)
📦 GitHub Release ← 🏷️ Auto-Tag ← 🤖 Auto-Merge ← ✅ Quality Checks ← 🔄 Convert
```

**Benefits:**
- **Prevents unnecessary runs** - only processes meaningful changes
- **Detailed decision logging** - full transparency on why actions were taken  
- **Fully automated releases** - from detection to GitHub release
- **Quality assurance** - automated checks before merging
- **Error resilience** - retry logic for transient failures

### Semi-Automated Workflow

For manual control with automated quality checks:

```bash
# Set credentials
export LORIS_USER=your_username
export LORIS_PASS=your_password

# Run update with quality checks
python scripts/automated_update.py --config config/pipeline.yml

# Review quality report (logs are gitignored locally)
# Check GitHub workflow artifacts for reports
```

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

## Repository Structure

```
├── config/                  # 🆕 Centralized configuration
│   ├── conversion.yml      # LORIS→ReproSchema mapping rules
│   ├── change_detection.yml # Smart detection thresholds
│   └── pipeline.yml        # Automation pipeline settings
├── reproschema_output/      # Generated ReproSchema files
│   ├── HBCD_LORIS/         # Protocol-level schema
│   └── activities/          # Activity-level schemas with items
├── loris_data_dictionaries/ # Source LORIS CSV files
├── scripts/                 # Conversion and automation scripts
│   ├── loris2reproschema.py # Main conversion script
│   ├── retrieve_script.py   # LORIS data fetcher
│   ├── automated_update.py  # Pipeline automation
│   └── detect_changes.py    # 🆕 Smart change detection
├── logs/                    # 🆕 Organized logs (gitignored)
│   ├── change_detection/   # Comparison reports
│   ├── conversion/         # Conversion process logs
│   └── validation/         # Schema validation logs  
├── notes/                   # Development notes
└── .github/workflows/       # 🆕 Automated CI/CD workflows
```

## Configuration

### Conversion Settings (`config/conversion.yml`)
Controls the LORIS→ReproSchema mapping:
- Column mappings from LORIS CSV to ReproSchema properties
- Field type mappings (e.g., "Dropdown" → "select")
- Metadata fields to include
- Domain/instrument grouping settings

### Change Detection (`config/change_detection.yml`)
Configures smart change detection sensitivity:
- Minimum thresholds for triggering conversion
- Columns to ignore (timestamps, metadata)
- Significant change percentage
- Field comparison rules

### Pipeline Settings (`config/pipeline.yml`)
Automation workflow configuration:
- Data retrieval settings
- Conversion parameters
- Validation options
- Quality check requirements

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

# Test change detection
python scripts/detect_changes.py --old-file old.csv --new-file new.csv
```

### Manual Pipeline Testing
```bash
# Test smart change detection
python scripts/detect_changes.py --old-file loris_data_dictionaries/hbcd_data_dictionary_2025-08-14.csv --new-file loris_data_dictionaries/hbcd_data_dictionary_2025-09-15.csv

# Test conversion pipeline
python scripts/automated_update.py --config config/pipeline.yml --csv-file path/to/specific/file.csv
```

## Known Issues

See [notes/ORIGINAL_DATA_ISSUES.md](notes/ORIGINAL_DATA_ISSUES.md) for documentation of source data quality issues and how the converter handles them.

## Monitoring & Troubleshooting

**Check pipeline status:**
- GitHub Actions tab shows workflow runs
- Change detection reports in workflow artifacts
- Quality reports available as workflow artifacts

**Common issues:**
- **LORIS API failures**: Pipeline has 3-attempt retry logic
- **YAML syntax errors**: Validate workflow files before commits
- **Change detection false negatives**: Adjust thresholds in `config/change_detection.yml`

**Getting help:**
- Check workflow logs in GitHub Actions
- Review comparison reports in artifacts
- Examine workflow run details for error traces

## Contributing

1. Create a feature branch
2. Make your changes  
3. Run validation and quality checks
4. Submit a pull request
5. Automated workflows will validate your changes

## License

MIT License - see [LICENSE](LICENSE) file for details

## Release Notes

**Latest**: The pipeline now includes smart change detection and automated releases. Only meaningful changes trigger conversions, with full automation from data retrieval to GitHub releases.