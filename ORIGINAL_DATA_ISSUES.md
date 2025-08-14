# LORIS Source Data Issues Documentation

This document tracks known data quality issues in the HBCD LORIS data dictionary that affect the ReproSchema conversion.

## 1. Typos and Spelling Errors

### 1.1 Question Text Typos

| Field | Issue | Current Text | Should Be | Status |
|-------|-------|--------------|-----------|---------|
| `sed_cg_ace_010` | Missing space | "vaginalintercourse" | "vaginal intercourse" | Auto-fixed in converter |
| `pex_bm_apa_1_mania_001` | Grammar error | "Sleeping less then usual" | "Sleeping less than usual" | Auto-fixed in converter |

## 2. Truncated Data

### 2.1 Activity Names

| Field | Issue | Current Value | Expected Format | Status |
|-------|-------|---------------|-----------------|---------|
| `adm_ra_fb_visit5_005` | Truncated activity name | "ecPROMIS (" | "ecPROMIS (<1 y/o) - Caregiver Child Relationship Scale" | Auto-fixed in converter (removes trailing "(") |

## 3. Missing Response Options

### 3.1 ACEs Questions (Yes/No/Don't Know)

These items appear to be Yes/No questions based on their content, but lack response options in the source data:

| Field | Question | Expected Choices | Current Type | Status |
|-------|----------|------------------|--------------|---------|
| `sed_cg_ace_001` | "Did you feel that you didn't have enough to eat..." | Yes/No/Don't know/Decline | Text | Source data issue |
| `sed_cg_ace_002` | "Did you lose a parent through divorce, abandonment..." | Yes/No/Don't know/Decline | Text | Source data issue |
| `sed_cg_ace_003` | "Did you live with anyone who was a problem drinker..." | Yes/No/Don't know/Decline | Text | Source data issue |
| `sed_cg_ace_004` | "Was a household member depressed, mentally ill..." | Yes/No/Don't know/Decline | Text | Source data issue |
| `sed_cg_ace_005` | "Did you live with anyone who went to jail or prison?" | Yes/No/Don't know/Decline | Text | Source data issue |
| `sed_cg_ace_006` | "Did a parent or adult in the household ever hit..." | Yes/No/Don't know/Decline | Text | Source data issue |
| `sed_cg_ace_007` | "Did a parent or adult in the household ever swear..." | Yes/No/Don't know/Decline | Text | Source data issue |
| `sed_cg_ace_008` | "Did anyone at least 5 years older than you..." | Yes/No/Don't know/Decline | Text | Source data issue |
| `sed_cg_ace_009` | "Did anyone at least 5 years older than you..." | Yes/No/Don't know/Decline | Text | Source data issue |
| `sed_cg_ace_010` | "Did you experience unwanted sexual contact..." | Yes/No/Don't know/Decline | Text | Source data issue |
| `sed_cg_ace_011` | "Were you in foster care?" | Yes/No/Don't know/Decline | Text | Source data issue |

## 4. Inconsistent Field Types

### 4.1 Fields with Choices but Text Input Type

These fields have response options defined but are marked as "Text" type instead of "Dropdown" or "Select":

| Activity | Fields Affected | Issue | Status |
|----------|----------------|-------|---------|
| Multiple activities | `Administration`, `Validity`, `Informant`, `Examiner` | Have choices but field_type="Text" | Converter attempts to fix |
| Multiple activities | Various date fields | "Date" validation but "Text" field type | Working as intended |

## 5. Redundant Variable Names

### 5.1 Duplicated Prefixes

| Field | Original Name | Issue | Fixed Name | Status |
|-------|--------------|-------|------------|---------|
| Food Insecurity | `sed_cg_foodins_sed_cg_foodins_category` | Prefix duplicated | `sed_cg_foodins_category` | Auto-fixed in converter |
| Behavior Observation | `mh_ch_bhvobs_mh_ch_bhvobs_arousal_before` | Prefix duplicated | `mh_ch_bhvobs_arousal_before` | Auto-fixed in converter |
| BM Screen | `adm_bm_screen_adm_bm_screen_001` | Prefix duplicated | `adm_bm_screen_001` | Auto-fixed in converter |

## 6. Invalid Date Constraints

### 6.1 Dynamic Date References

Many fields use dynamic date references that cannot be validated statically:

| Pattern | Example | Issue | Count |
|---------|---------|-------|-------|
| `today` | max_value: "today" | Dynamic reference | 200+ occurrences |
| `[field_reference]` | min_value: "[screening_arm_1][setup_lmp]" | Field reference | 100+ occurrences |
| `[relative_field]` | min_value: "[health_er_start_01]" | Relative field reference | 50+ occurrences |

## 7. Missing Field Metadata

### 7.1 Examiner Field Choices

The following fields are marked as "select" type but have no predefined examiner list:

- `sed_cg_ace_Examiner`
- `sed_cg_foodins_Examiner`
- `pex_bm_apa_Examiner`
- And many others...

**Recommendation**: LORIS should provide a standard list of examiner choices or these should be free text fields.

## 8. DICOM Naming Convention

### 8.1 Colon Usage in Parameter Names

| Pattern | Example | Issue | Status |
|---------|---------|-------|---------|
| DICOM parameters | `dicom_0x0018:el_0x1090` | Colons invalid in file names | Auto-fixed in converter (replaced with underscore) |

## Recommendations

1. **ACEs Response Options**: Add proper Yes/No/Don't know/Decline to answer choices for all ACEs items
2. **Field Type Consistency**: Review fields with choices and ensure they use appropriate field types (Dropdown/Select)
3. **Examiner Lists**: Provide standardized examiner choice lists or change to text fields
4. **Activity Name Validation**: Add validation to prevent truncated activity names in data entry
5. **Variable Name Validation**: Add checks to prevent redundant prefixes in variable names
6. **Documentation**: Document the expected format for dynamic date constraints

## Converter Mitigations

The `loris2reproschema.py` converter includes the following automatic fixes:

1. **Typo Corrections**: Common typos are automatically corrected during conversion
2. **Truncated Names**: Activity names ending with " (" are cleaned up
3. **Redundant Prefixes**: Duplicated prefixes in variable names are detected and removed
4. **DICOM Names**: Colons in DICOM parameter names are replaced with underscores
5. **Trailing Spaces**: Whitespace is trimmed from visibility conditions
6. **Field Type Inference**: When choices are present but field type is "text", attempts to update to "select"

## Last Updated

2025-08-14 - Based on HBCD data dictionary version 2025-08-14