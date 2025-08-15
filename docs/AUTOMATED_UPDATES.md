# Automated LORIS to ReproSchema Updates

This document describes the semi-automated update pipeline for converting HBCD LORIS data dictionaries to ReproSchema format.

## Overview

The update pipeline provides automated conversion with built-in quality checks and human review checkpoints. This balances automation efficiency with quality assurance.

## Components

### 1. Automated Update Script (`scripts/automated_update.py`)

The main orchestration script that:
- Retrieves latest LORIS data dictionary
- Runs conversion with quality tracking
- Validates generated schemas
- Performs quality checks
- Generates detailed reports

```bash
# Basic usage
python scripts/automated_update.py

# With custom config
python scripts/automated_update.py --config my_config.yml
```

### 2. Enhanced Converter (`scripts/loris2reproschema.py`)

Now includes:
- Quality report generation
- Automatic issue detection
- Fix tracking
- Statistics collection

### 3. GitHub Actions Workflow (`.github/workflows/automated_update.yml`)

Scheduled automation that:
- Runs weekly updates
- Creates PRs for review
- Generates quality reports
- Notifies on failures

### 4. Pre-commit Hooks (`.pre-commit-config.yaml`)

Local validation including:
- JSON/YAML syntax checking
- ReproSchema validation
- Data quality checks
- Code formatting

### 5. Data Quality Checker (`scripts/check_data_quality.py`)

Standalone tool for:
- ACEs item validation
- Select field checking
- Naming convention validation
- Protocol schema verification

## Configuration

### Update Configuration (`update_config.yml`)

```yaml
loris:
  username: ${LORIS_USER}  # From environment
  password: ${LORIS_PASS}  # From environment
  output_dir: loris_data_dictionaries

conversion:
  config_file: hbcd-loris.yml
  output_path: reproschema_output

validation:
  enabled: true
  stop_on_error: true

quality_checks:
  check_aces: true
  check_typos: true
  check_truncation: true
  check_naming: true
  max_issues_threshold: 50

git:
  auto_commit: false  # Set to true for full automation
  branch_prefix: auto-update
  create_pr: false    # Set to true for PR creation
```

## Workflow

### Manual Semi-Automated Update

1. **Run the automated update script:**
```bash
export LORIS_USER=your_username
export LORIS_PASS=your_password
python scripts/automated_update.py
```

2. **Review the quality report:**
```bash
cat quality_report_*.json | jq .
```

3. **Check for issues:**
- Review `issues` section for problems found
- Check `fixes_applied` for automatic corrections
- Note any `warnings` that need attention

4. **If satisfied, commit changes:**
```bash
git add reproschema_output/
git commit -m "Update from LORIS data dictionary $(date +%Y-%m-%d)"
```

### Fully Automated (GitHub Actions)

The workflow runs weekly and:
1. Retrieves latest data
2. Runs conversion
3. Creates branch with changes
4. Opens PR for review
5. Includes quality report

To enable:
1. Set GitHub secrets: `HBCD_USERNAME` and `HBCD_PASSWORD`
2. Enable GitHub Actions in repository
3. Review and merge PRs as they're created

## Quality Checks

### Automatic Fixes Applied

- **Typos**: "vaginalintercourse" → "vaginal intercourse"
- **Truncated names**: "ecPROMIS (" → "ecPROMIS"
- **Redundant prefixes**: Removes duplicated prefixes
- **Multiple underscores**: Collapses to single underscore
- **Special characters**: Replaces with underscores

### Issues Detected

- ACEs items without proper choices
- Select fields missing response options
- Inconsistent field types
- Invalid naming conventions
- Truncated activity names

### Reports Generated

Each run produces:
- `quality_report_TIMESTAMP.json`: Detailed quality report
- `update_report_TIMESTAMP.json`: Update process summary
- `logs/update_TIMESTAMP.log`: Detailed execution log

## Manual Intervention

Required when:
- Quality check threshold exceeded (>50 issues by default)
- Validation failures occur
- New types of issues appear
- Schema structure changes needed

## Monitoring

### Success Indicators
- All steps complete successfully
- Issues count within threshold
- Validation passes
- No critical warnings

### Failure Notifications
- GitHub issue created on workflow failure
- Detailed logs available in artifacts
- Quality report highlights problems

## Best Practices

1. **Regular Reviews**: Even with automation, review PRs carefully
2. **Monitor Trends**: Track issue counts over time
3. **Update Fixes**: Add new automatic fixes as patterns emerge
4. **Test Locally**: Run manual updates before enabling full automation
5. **Backup**: Keep previous versions for rollback if needed

## Troubleshooting

### Common Issues

1. **Authentication fails**
   - Check LORIS credentials in environment
   - Verify network access to LORIS

2. **Validation errors**
   - Review schema structure
   - Check for missing required fields
   - Validate context URLs

3. **Too many quality issues**
   - Review source data quality
   - Adjust threshold if appropriate
   - Add new automatic fixes

4. **Git conflicts**
   - Pull latest changes before running
   - Resolve conflicts manually
   - Consider rebasing branch

## Future Enhancements

- Dashboard for quality metrics
- Slack/email notifications
- Differential updates (only changed items)
- Automatic rollback on critical failures
- Machine learning for issue detection