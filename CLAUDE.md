# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository converts HBCD (HEALthy Brain and Child Development) study data from LORIS format to ReproSchema format. ReproSchema is a standardized format for representing questionnaires and assessments in research studies.

## Key Architecture

### Three-layer ReproSchema Structure:
1. **Protocol level**: Top-level study protocol (e.g., HBCD_LORIS)
2. **Activity level**: Individual instruments/assessments (e.g., ERICA_3_to_7_months, adm_bm_screen)
3. **Item level**: Individual questions/fields within each activity

### Core Components:
- **loris2reproschema.py**: Main converter script that processes LORIS CSV data dictionary into ReproSchema JSON format
- **retrieve_script.py**: Fetches HBCD data dictionary from LORIS API
- **config/conversion.yml**: Configuration file defining mappings between LORIS columns and ReproSchema properties

## Workflow

### Standard Update Process:
1. **Create new branch** for the update (e.g., `YYYY-MM-DD-update` or descriptive name)
2. **Retrieve** latest HBCD data dictionary from LORIS
3. **Convert** LORIS format to ReproSchema format
4. **Validate** the generated schemas
5. **Create PR** and merge to main if validation passes
6. **Create tag and release** on main branch

## Environment Setup

### Create and activate micromamba environment:
```bash
# Create environment
micromamba create -n hbcd python=3.10

# Activate environment
micromamba activate hbcd

# Install required packages
micromamba install -c conda-forge requests pandas pyyaml beautifulsoup4
pip install reproschema
```

## Common Commands

### 1. Fetch latest data dictionary from LORIS:
```bash
# Make sure hbcd environment is activated first
micromamba activate hbcd
python scripts/retrieve_script.py --username YOUR_USERNAME --password YOUR_PASSWORD --output_dir loris_data_dictionaries/
```

### 2. Convert LORIS data to ReproSchema:
```bash
python scripts/loris2reproschema.py --csv_file loris_data_dictionaries/hbcd_data_dictionary_YYYY-MM-DD.csv --config_file config/conversion.yml --output_path loris2reproschema/
```

### 3. Validate generated schemas:
```bash
# Install reproschema-py if needed
pip install reproschema

# Validate the protocol
reproschema validate HBCD_LORIS/HBCD_LORIS_schema

# Validate individual activities (example)
reproschema validate activities/*/[activity_name]_schema
```

### Complete workflow example:
```bash
# 1. Create and checkout new branch
git checkout -b 2025-05-20-update

# 2. Fetch latest data dictionary
python scripts/retrieve_script.py --username $LORIS_USER --password $LORIS_PASS --output_dir loris_data_dictionaries/

# 3. Run conversion
python scripts/loris2reproschema.py --csv_file loris_data_dictionaries/hbcd_data_dictionary_2025-05-20.csv --config_file config/conversion.yml --output_path loris2reproschema/

# 4. Validate (requires reproschema-py)
reproschema validate HBCD_LORIS/HBCD_LORIS_schema

# 5. Commit changes
git add .
git commit -m "Update HBCD schemas from LORIS data dictionary YYYY-MM-DD"

# 6. Push and create PR
git push origin 2025-05-20-update
# Create PR via GitHub UI or CLI

# 7. After merge to main, create release
git checkout main
git pull
git tag -a v1.0.0-YYYY-MM-DD -m "Release based on LORIS data dictionary YYYY-MM-DD"
git push origin v1.0.0-YYYY-MM-DD
```

## Directory Structure

- `activities/`: Generated ReproSchema activity definitions (one per instrument)
- `loris_data_dictionaries/`: Source LORIS CSV data dictionaries
- `HBCD_LORIS/`: Generated protocol-level schema
- `scripts/`: Python conversion scripts

## Important Configuration

The `config/conversion.yml` file defines:
- Column mappings from LORIS CSV to ReproSchema properties
- Field type mappings (e.g., "Dropdown" → "select")
- Which columns to include as metadata notes
- Domain/instrument grouping column (default: "full_instrument_name")

## Data Flow

1. LORIS CSV data dictionary → 
2. loris2reproschema.py reads CSV and config → 
3. Groups items by instrument/domain → 
4. Creates JSON schemas following ReproSchema specification → 
5. Outputs hierarchical structure (protocol/activities/items)