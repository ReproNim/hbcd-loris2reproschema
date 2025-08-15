#!/usr/bin/env python
"""
Automated HBCD LORIS to ReproSchema Update Pipeline

This script provides a semi-automated workflow for updating ReproSchema
from LORIS data dictionary with built-in quality checks and validation.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yaml


class UpdatePipeline:
    """Manages the automated update pipeline with quality checks."""
    
    def __init__(self, config_path: str = "update_config.yml"):
        """Initialize the update pipeline."""
        self.config = self._load_config(config_path)
        self.timestamp = datetime.now().strftime("%Y-%m-%d")
        self.report = {
            "timestamp": self.timestamp,
            "steps": [],
            "issues": [],
            "warnings": [],
            "success": True
        }
        
        # Setup logging
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / f"update_{self.timestamp}.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            # Create default config
            default_config = {
                "loris": {
                    "username": "${LORIS_USER}",
                    "password": "${LORIS_PASS}",
                    "output_dir": "loris_data_dictionaries"
                },
                "conversion": {
                    "config_file": "hbcd-loris.yml",
                    "output_path": "reproschema_output"
                },
                "validation": {
                    "enabled": True,
                    "stop_on_error": True
                },
                "quality_checks": {
                    "check_aces": True,
                    "check_typos": True,
                    "check_truncation": True,
                    "check_naming": True,
                    "max_issues_threshold": 50
                },
                "git": {
                    "auto_commit": False,
                    "branch_prefix": "auto-update",
                    "create_pr": False
                }
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False)
            
            self.logger.info(f"Created default config at {config_path}")
            return default_config
        
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _run_command(self, cmd: List[str], description: str) -> Tuple[bool, str]:
        """Run a shell command and capture output."""
        self.logger.info(f"Running: {description}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            self.report["steps"].append({
                "step": description,
                "status": "success",
                "output": result.stdout
            })
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed: {description}")
            self.logger.error(f"Error: {e.stderr}")
            self.report["steps"].append({
                "step": description,
                "status": "failed",
                "error": e.stderr
            })
            self.report["success"] = False
            return False, e.stderr
    
    def step1_retrieve_data(self) -> bool:
        """Step 1: Retrieve latest LORIS data dictionary."""
        self.logger.info("=" * 50)
        self.logger.info("STEP 1: Retrieving LORIS Data Dictionary")
        self.logger.info("=" * 50)
        
        # Expand environment variables
        username = os.path.expandvars(self.config["loris"]["username"])
        password = os.path.expandvars(self.config["loris"]["password"])
        output_dir = self.config["loris"]["output_dir"]
        
        if username == "${LORIS_USER}" or password == "${LORIS_PASS}":
            self.logger.error("LORIS credentials not set in environment")
            return False
        
        cmd = [
            sys.executable,
            "scripts/retrieve_script.py",
            "--username", username,
            "--password", password,
            "--output_dir", output_dir
        ]
        
        success, _ = self._run_command(cmd, "Retrieving LORIS data dictionary")
        
        if success:
            # Find the downloaded file
            self.csv_file = Path(output_dir) / f"hbcd_data_dictionary_{self.timestamp}.csv"
            if not self.csv_file.exists():
                # Try to find any recent CSV
                csv_files = sorted(Path(output_dir).glob("*.csv"))
                if csv_files:
                    self.csv_file = csv_files[-1]
                    self.logger.info(f"Using CSV file: {self.csv_file}")
                else:
                    self.logger.error("No CSV file found after retrieval")
                    return False
        
        return success
    
    def step2_convert_data(self) -> bool:
        """Step 2: Convert LORIS to ReproSchema format."""
        self.logger.info("=" * 50)
        self.logger.info("STEP 2: Converting to ReproSchema")
        self.logger.info("=" * 50)
        
        cmd = [
            sys.executable,
            "scripts/loris2reproschema.py",
            "--csv_file", str(self.csv_file),
            "--config_file", self.config["conversion"]["config_file"],
            "--output_path", self.config["conversion"]["output_path"]
        ]
        
        success, _ = self._run_command(cmd, "Converting LORIS to ReproSchema")
        return success
    
    def step3_validate_schemas(self) -> bool:
        """Step 3: Validate generated schemas."""
        if not self.config["validation"]["enabled"]:
            self.logger.info("Validation disabled in config")
            return True
        
        self.logger.info("=" * 50)
        self.logger.info("STEP 3: Validating Schemas")
        self.logger.info("=" * 50)
        
        output_path = Path(self.config["conversion"]["output_path"])
        protocol_schema = output_path / "HBCD_LORIS" / "HBCD_LORIS_schema"
        
        cmd = [
            "reproschema",
            "validate",
            str(protocol_schema)
        ]
        
        success, output = self._run_command(cmd, "Validating protocol schema")
        
        if not success and self.config["validation"]["stop_on_error"]:
            self.logger.error("Validation failed, stopping pipeline")
            return False
        
        return True
    
    def step4_quality_checks(self) -> bool:
        """Step 4: Run quality checks on converted data."""
        self.logger.info("=" * 50)
        self.logger.info("STEP 4: Running Quality Checks")
        self.logger.info("=" * 50)
        
        checks = self.config["quality_checks"]
        issues_found = []
        
        output_path = Path(self.config["conversion"]["output_path"])
        
        # Check for ACEs items without choices
        if checks["check_aces"]:
            self.logger.info("Checking ACEs items...")
            aces_path = output_path / "activities" / "Pediatric_ACEs"
            if aces_path.exists():
                for item_file in aces_path.glob("items/*.json"):
                    with open(item_file) as f:
                        item = json.load(f)
                    
                    if "ace_0" in item_file.name:
                        if item.get("ui", {}).get("inputType") == "text":
                            issues_found.append({
                                "type": "aces_missing_choices",
                                "file": str(item_file),
                                "item": item_file.stem
                            })
        
        # Check for known typos
        if checks["check_typos"]:
            self.logger.info("Checking for typos...")
            typo_patterns = [
                "vaginalintercourse",
                "less then usual"
            ]
            
            for activity_dir in (output_path / "activities").iterdir():
                if activity_dir.is_dir():
                    for item_file in (activity_dir / "items").glob("*.json"):
                        with open(item_file) as f:
                            content = f.read()
                        
                        for typo in typo_patterns:
                            if typo in content:
                                issues_found.append({
                                    "type": "typo",
                                    "file": str(item_file),
                                    "typo": typo
                                })
        
        # Check for truncated names
        if checks["check_truncation"]:
            self.logger.info("Checking for truncated names...")
            protocol_file = output_path / "HBCD_LORIS" / "HBCD_LORIS_schema"
            with open(protocol_file) as f:
                protocol = json.load(f)
            
            for activity in protocol.get("ui", {}).get("order", []):
                if isinstance(activity, dict):
                    name = activity.get("name", "")
                    if name.endswith(" ("):
                        issues_found.append({
                            "type": "truncated_name",
                            "activity": name
                        })
        
        # Check naming conventions
        if checks["check_naming"]:
            self.logger.info("Checking naming conventions...")
            for activity_dir in (output_path / "activities").iterdir():
                if activity_dir.is_dir():
                    if "__" in activity_dir.name or "___" in activity_dir.name:
                        issues_found.append({
                            "type": "naming_convention",
                            "directory": str(activity_dir),
                            "issue": "multiple_underscores"
                        })
        
        # Record issues
        self.report["issues"] = issues_found
        
        # Check threshold
        if len(issues_found) > checks["max_issues_threshold"]:
            self.logger.error(f"Too many issues found: {len(issues_found)} > {checks['max_issues_threshold']}")
            self.report["success"] = False
            return False
        elif issues_found:
            self.logger.warning(f"Found {len(issues_found)} issues (within threshold)")
            self.report["warnings"].append(f"Quality checks found {len(issues_found)} issues")
        else:
            self.logger.info("No quality issues found")
        
        return True
    
    def step5_generate_report(self) -> None:
        """Step 5: Generate quality report."""
        self.logger.info("=" * 50)
        self.logger.info("STEP 5: Generating Report")
        self.logger.info("=" * 50)
        
        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)
        
        report_file = report_dir / f"update_report_{self.timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(self.report, f, indent=2)
        
        self.logger.info(f"Report saved to: {report_file}")
        
        # Generate summary
        print("\n" + "=" * 50)
        print("UPDATE SUMMARY")
        print("=" * 50)
        print(f"Timestamp: {self.timestamp}")
        print(f"Success: {self.report['success']}")
        print(f"Steps completed: {sum(1 for s in self.report['steps'] if s['status'] == 'success')}/{len(self.report['steps'])}")
        print(f"Issues found: {len(self.report['issues'])}")
        print(f"Warnings: {len(self.report['warnings'])}")
        
        if self.report['issues']:
            print("\nTop issues:")
            issue_types = {}
            for issue in self.report['issues']:
                issue_type = issue.get('type', 'unknown')
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
            
            for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  - {issue_type}: {count}")
    
    def step6_git_operations(self) -> bool:
        """Step 6: Optional Git operations."""
        if not self.config["git"]["auto_commit"]:
            self.logger.info("Git auto-commit disabled")
            return True
        
        self.logger.info("=" * 50)
        self.logger.info("STEP 6: Git Operations")
        self.logger.info("=" * 50)
        
        # Create branch
        branch_name = f"{self.config['git']['branch_prefix']}-{self.timestamp}"
        self._run_command(["git", "checkout", "-b", branch_name], f"Creating branch {branch_name}")
        
        # Add files
        self._run_command(["git", "add", self.config["conversion"]["output_path"]], "Adding converted files")
        
        # Commit
        commit_msg = f"Automated update from LORIS data dictionary {self.timestamp}\n\n"
        commit_msg += f"Issues found: {len(self.report['issues'])}\n"
        commit_msg += f"Warnings: {len(self.report['warnings'])}"
        
        self._run_command(["git", "commit", "-m", commit_msg], "Committing changes")
        
        if self.config["git"]["create_pr"]:
            self.logger.info("PR creation enabled - would create PR here")
            # PR creation would go here
        
        return True
    
    def run(self) -> bool:
        """Run the complete update pipeline."""
        steps = [
            self.step1_retrieve_data,
            self.step2_convert_data,
            self.step3_validate_schemas,
            self.step4_quality_checks,
            self.step5_generate_report
        ]
        
        for step in steps:
            if not step():
                if step.__name__ != 'step5_generate_report':  # Always generate report
                    self.step5_generate_report()
                return False
        
        # Optional git operations
        if self.config["git"]["auto_commit"]:
            self.step6_git_operations()
        
        return self.report["success"]


def main():
    parser = argparse.ArgumentParser(description="Automated HBCD LORIS to ReproSchema update")
    parser.add_argument("--config", default="update_config.yml", help="Configuration file path")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    args = parser.parse_args()
    
    pipeline = UpdatePipeline(args.config)
    success = pipeline.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()