#!/usr/bin/env python
"""
Data quality checker for ReproSchema conversion.

This script performs basic quality checks on the converted ReproSchema files
and can be used as a pre-commit hook or standalone validation tool.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def check_aces_items(activities_path: Path) -> List[str]:
    """Check ACEs items for proper configuration."""
    issues = []
    aces_path = activities_path / "Pediatric_ACEs"
    
    if not aces_path.exists():
        return issues
    
    items_path = aces_path / "items"
    if not items_path.exists():
        return issues
    
    for item_file in items_path.glob("sed_cg_ace_*.json"):
        with open(item_file) as f:
            item = json.load(f)
        
        # Check if ACEs items have proper select input type
        input_type = item.get("ui", {}).get("inputType")
        choices = item.get("responseOptions", {}).get("choices", [])
        
        if "ace_00" in item_file.name or "ace_01" in item_file.name:
            if input_type == "text":
                issues.append(f"ACEs item {item_file.stem} has text input but should be select")
            if not choices:
                issues.append(f"ACEs item {item_file.stem} is missing response choices")
    
    return issues


def check_select_fields(activities_path: Path) -> List[str]:
    """Check that select fields have choices defined."""
    issues = []
    
    for activity_dir in activities_path.iterdir():
        if not activity_dir.is_dir():
            continue
        
        items_path = activity_dir / "items"
        if not items_path.exists():
            continue
        
        for item_file in items_path.glob("*.json"):
            with open(item_file) as f:
                item = json.load(f)
            
            input_type = item.get("ui", {}).get("inputType")
            choices = item.get("responseOptions", {}).get("choices", [])
            
            if input_type in ["select", "selectMultiple", "radio", "checkbox"]:
                if not choices:
                    issues.append(f"{activity_dir.name}/{item_file.stem}: select field missing choices")
    
    return issues


def check_naming_conventions(activities_path: Path) -> List[str]:
    """Check for naming convention issues."""
    issues = []
    
    for activity_dir in activities_path.iterdir():
        if not activity_dir.is_dir():
            continue
        
        # Check for multiple underscores
        if "__" in activity_dir.name or "___" in activity_dir.name:
            issues.append(f"Activity name has multiple underscores: {activity_dir.name}")
        
        # Check for special characters that shouldn't be there
        if any(char in activity_dir.name for char in [":", "/", "\\", "?", "*", "|", "<", ">"]):
            issues.append(f"Activity name has invalid characters: {activity_dir.name}")
    
    return issues


def check_protocol_schema(protocol_path: Path) -> List[str]:
    """Check protocol schema for common issues."""
    issues = []
    
    schema_file = protocol_path / "HBCD_LORIS_schema"
    if not schema_file.exists():
        return ["Protocol schema not found"]
    
    with open(schema_file) as f:
        protocol = json.load(f)
    
    # Check for truncated activity names
    for activity in protocol.get("ui", {}).get("order", []):
        if isinstance(activity, dict):
            name = activity.get("name", "")
            if name.endswith(" ("):
                issues.append(f"Truncated activity name in protocol: {name}")
    
    return issues


def main():
    """Run all quality checks."""
    output_path = Path("reproschema_output")
    
    if not output_path.exists():
        print("No reproschema_output directory found, skipping checks")
        return 0
    
    all_issues = []
    
    # Run checks
    # Prefer activities nested under the protocol folder; fallback to root-level
    activities_path = output_path / "HBCD_LORIS" / "activities"
    if not activities_path.exists():
        activities_path = output_path / "activities"
    if activities_path.exists():
        all_issues.extend(check_aces_items(activities_path))
        all_issues.extend(check_select_fields(activities_path))
        all_issues.extend(check_naming_conventions(activities_path))
    
    protocol_path = output_path / "HBCD_LORIS"
    if protocol_path.exists():
        all_issues.extend(check_protocol_schema(protocol_path))
    
    # Report results
    if all_issues:
        print(f"Found {len(all_issues)} data quality issues:")
        for issue in all_issues[:10]:  # Show first 10 issues
            print(f"  - {issue}")
        if len(all_issues) > 10:
            print(f"  ... and {len(all_issues) - 10} more")
        
        # Don't fail pre-commit, just warn
        return 0
    else:
        print("All data quality checks passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
