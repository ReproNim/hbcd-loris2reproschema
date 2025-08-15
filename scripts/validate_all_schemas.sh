#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Get current timestamp for log file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/validation_${TIMESTAMP}.log"
ERROR_LOG="logs/validation_errors_${TIMESTAMP}.log"
SUMMARY_LOG="logs/validation_summary_${TIMESTAMP}.log"

echo "Starting validation of all schemas at $(date)" | tee $LOG_FILE
echo "================================================" | tee -a $LOG_FILE

# Use micromamba run to execute commands in the hbcd environment
MICROMAMBA_RUN="$(which micromamba) run -n hbcd"

# Counter for tracking
TOTAL=0
SUCCESS=0
FAILED=0

# First, validate the main protocol schema
echo -e "\n1. Validating main protocol schema..." | tee -a $LOG_FILE $SUMMARY_LOG
if $MICROMAMBA_RUN reproschema validate HBCD_LORIS/HBCD_LORIS_schema >> $LOG_FILE 2>&1; then
    echo "✓ HBCD_LORIS protocol validated successfully" | tee -a $LOG_FILE $SUMMARY_LOG
    ((SUCCESS++))
else
    echo "✗ HBCD_LORIS protocol validation failed" | tee -a $LOG_FILE $SUMMARY_LOG
    echo "HBCD_LORIS/HBCD_LORIS_schema" >> $ERROR_LOG
    ((FAILED++))
fi
((TOTAL++))

# Count activities for progress tracking
ACTIVITY_COUNT=$(ls -d activities/*/ 2>/dev/null | wc -l)
CURRENT=0

# Validate each activity schema (not individual items)
echo -e "\n2. Validating activity schemas ($ACTIVITY_COUNT activities)..." | tee -a $LOG_FILE $SUMMARY_LOG
for activity_dir in activities/*/; do
    if [ -d "$activity_dir" ]; then
        ((CURRENT++))
        activity_name=$(basename "$activity_dir")
        schema_file="${activity_dir}${activity_name}_schema"
        
        if [ -f "$schema_file" ]; then
            echo -n "[$CURRENT/$ACTIVITY_COUNT] Validating $activity_name... " | tee -a $LOG_FILE
            
            # Run validation with timeout to prevent hanging
            if timeout 30 $MICROMAMBA_RUN reproschema validate "$schema_file" >> $LOG_FILE 2>&1; then
                echo "✓" | tee -a $LOG_FILE
                echo "✓ $activity_name" >> $SUMMARY_LOG
                ((SUCCESS++))
            else
                echo "✗" | tee -a $LOG_FILE
                echo "✗ $activity_name" >> $SUMMARY_LOG
                echo "$schema_file" >> $ERROR_LOG
                ((FAILED++))
            fi
            ((TOTAL++))
        else
            echo "[$CURRENT/$ACTIVITY_COUNT] Warning: Schema file not found for $activity_name" | tee -a $LOG_FILE $SUMMARY_LOG
        fi
    fi
done

# Optional: Validate entire activities directory in one go (in background)
echo -e "\n3. Running comprehensive validation on activities directory..." | tee -a $LOG_FILE $SUMMARY_LOG
echo "(This may take several minutes)" | tee -a $LOG_FILE

# Run with timeout and capture output
if timeout 300 $MICROMAMBA_RUN reproschema validate activities/ >> $LOG_FILE 2>&1; then
    echo "✓ Full activities directory validation passed" | tee -a $LOG_FILE $SUMMARY_LOG
else
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo "⚠ Full validation timed out after 5 minutes (individual validations above still valid)" | tee -a $LOG_FILE $SUMMARY_LOG
    else
        echo "✗ Full activities directory validation failed" | tee -a $LOG_FILE $SUMMARY_LOG
    fi
fi

# Summary
echo -e "\n================================================" | tee -a $SUMMARY_LOG
echo "VALIDATION SUMMARY" | tee -a $SUMMARY_LOG
echo "================================================" | tee -a $SUMMARY_LOG
echo "Total schemas validated: $TOTAL" | tee -a $SUMMARY_LOG
echo "Successful: $SUCCESS" | tee -a $SUMMARY_LOG
echo "Failed: $FAILED" | tee -a $SUMMARY_LOG

if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=2; $SUCCESS * 100 / $TOTAL" | bc)
    echo "Success rate: ${SUCCESS_RATE}%" | tee -a $SUMMARY_LOG
fi

echo -e "\nLog files created:" | tee -a $SUMMARY_LOG
echo "  - Full log: $LOG_FILE" | tee -a $SUMMARY_LOG
echo "  - Summary: $SUMMARY_LOG" | tee -a $SUMMARY_LOG

if [ $FAILED -gt 0 ]; then
    echo "  - Failed schemas: $ERROR_LOG" | tee -a $SUMMARY_LOG
    echo -e "\n⚠ Some schemas failed validation. Please review the error log." | tee -a $SUMMARY_LOG
    exit 1
else
    echo -e "\n✅ All schemas validated successfully!" | tee -a $SUMMARY_LOG
    exit 0
fi