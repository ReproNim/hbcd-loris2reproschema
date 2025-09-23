#!/usr/bin/env python
"""
Simple Automated HBCD LORIS to ReproSchema Update Pipeline

This script provides a simple, reliable workflow for updating ReproSchema
from LORIS data dictionary with basic error handling.
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
    """Simple pipeline for LORIS to ReproSchema conversion."""

    def __init__(self, config_path: str = "config/pipeline.yml"):
        """Initialize the update pipeline."""
        self.config = self._load_config(config_path)
        self.timestamp = datetime.now().strftime("%Y-%m-%d")
        self.report = {
            "timestamp": self.timestamp,
            "steps": [],
            "issues": [],
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
                    "config_file": "config/conversion.yml",
                    "output_path": "reproschema_output"
                },
                "validation": {
                    "enabled": True,
                    "stop_on_error": true
                },
                "quality_checks": {
                    "max_issues_threshold": 50
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
        self.logger.info(f"Command: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"Command completed successfully")
            if result.stdout:
                self.logger.info(f"Stdout: {result.stdout[:500]}...")  # First 500 chars
            self.report["steps"].append({
                "step": description,
                "status": "success"
            })
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed: {description}")
            self.logger.error(f"Exit code: {e.returncode}")
            self.logger.error(f"Command: {' '.join(cmd)}")
            if e.stdout:
                self.logger.error(f"Stdout: {e.stdout}")
            if e.stderr:
                self.logger.error(f"Stderr: {e.stderr}")
            else:
                self.logger.error("No stderr output captured")
            self.report["steps"].append({
                "step": description,
                "status": "failed",
                "error": e.stderr or f"Exit code {e.returncode}, no stderr",
                "exit_code": e.returncode,
                "stdout": e.stdout
            })
            self.report["success"] = False
            return False, e.stderr or f"Exit code {e.returncode}"

    def _cleanup_partial_output(self) -> None:
        """Clean up any partial conversion output."""
        output_path = Path(self.config["conversion"]["output_path"])

        if output_path.exists():
            try:
                # Remove any incomplete protocol directories
                protocol_dirs = [d for d in output_path.iterdir() if d.is_dir() and d.name.startswith("HBCD")]
                for proto_dir in protocol_dirs:
                    schema_file = proto_dir / f"{proto_dir.name}_schema"
                    if not schema_file.exists() or schema_file.stat().st_size == 0:
                        self.logger.info(f"Removing incomplete protocol directory: {proto_dir}")
                        import shutil
                        shutil.rmtree(proto_dir)

            except Exception as e:
                self.logger.warning(f"Error during cleanup: {e}")

    def step1_get_data(self, csv_file_path: str = None) -> bool:
        """Step 1: Get LORIS data dictionary."""
        self.logger.info("=" * 50)
        self.logger.info("STEP 1: Getting LORIS Data Dictionary")
        self.logger.info("=" * 50)

        # If a specific CSV file is provided, use it
        if csv_file_path:
            self.csv_file = Path(csv_file_path)
            if not self.csv_file.exists():
                self.logger.error(f"Provided CSV file not found: {csv_file_path}")
                return False

            # Basic CSV validation
            try:
                df = pd.read_csv(self.csv_file, nrows=1)  # Just read 1 row to test
                if df.empty:
                    self.logger.error("CSV file is empty or invalid")
                    return False
            except Exception as e:
                self.logger.error(f"CSV file validation failed: {e}")
                return False

            self.logger.info(f"Using provided CSV file: {self.csv_file}")
            return True

        # Otherwise, find the most recent CSV file
        output_dir = self.config["loris"]["output_dir"]
        csv_files = sorted(Path(output_dir).glob("hbcd_data_dictionary_*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)

        if csv_files:
            self.csv_file = csv_files[0]
            self.logger.info(f"Using most recent CSV file: {self.csv_file}")
            return True

        self.logger.error("No CSV files found and none provided")
        return False

    def step2_convert_data(self) -> bool:
        """Step 2: Convert LORIS to ReproSchema format."""
        self.logger.info("=" * 50)
        self.logger.info("STEP 2: Converting to ReproSchema")
        self.logger.info("=" * 50)

        # Basic validation
        if not self.csv_file.exists():
            self.logger.error(f"CSV file not found: {self.csv_file}")
            return False

        # Clean any existing partial output
        self._cleanup_partial_output()

        cmd = [
            sys.executable,
            "scripts/loris2reproschema.py",
            "--csv_file", str(self.csv_file),
            "--config_file", self.config["conversion"]["config_file"],
            "--output_path", self.config["conversion"]["output_path"]
        ]

        success, output = self._run_command(cmd, "Converting LORIS to ReproSchema")

        if not success:
            self.logger.error("Conversion failed")
            self._cleanup_partial_output()
            return False

        self.logger.info("Conversion completed successfully")
        return True

    def step3_validate_schemas(self) -> bool:
        """Step 3: Validate generated schemas."""
        if not self.config["validation"]["enabled"]:
            self.logger.info("Validation disabled in config")
            return True

        self.logger.info("=" * 50)
        self.logger.info("STEP 3: Validating Schemas")
        self.logger.info("=" * 50)

        output_path = Path(self.config["conversion"]["output_path"])
        protocol_schema = output_path / "HBCD_LORIS" / "HBCD_LORIS" / "HBCD_LORIS_schema"

        if not protocol_schema.exists():
            self.logger.error("Protocol schema not found")
            return False

        cmd = [
            "reproschema",
            "validate",
            str(protocol_schema)
        ]

        success, output = self._run_command(cmd, "Validating protocol schema")

        if not success:
            self.logger.error("Schema validation failed")
            if self.config["validation"]["stop_on_error"]:
                return False
        else:
            self.logger.info("Schema validation passed")

        return True

    def step4_generate_report(self) -> bool:
        """Step 4: Generate simple report."""
        self.logger.info("=" * 50)
        self.logger.info("STEP 4: Generating Report")
        self.logger.info("=" * 50)

        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)

        report_file = report_dir / f"update_report_{self.timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(self.report, f, indent=2)

        self.logger.info(f"Report saved to: {report_file}")

        # Simple summary
        print("\n" + "=" * 50)
        print("UPDATE SUMMARY")
        print("=" * 50)
        print(f"Timestamp: {self.timestamp}")
        print(f"Success: {self.report['success']}")
        print(f"Steps completed: {sum(1 for s in self.report['steps'] if s['status'] == 'success')}/{len(self.report['steps'])}")

        return True

    def step5_generate_comparisons(self) -> bool:
        """Step 5: Generate comparison files for web interface."""
        if not self.config.get("comparisons", {}).get("enabled", True):
            self.logger.info("Comparison generation disabled in config")
            return True

        self.logger.info("=" * 50)
        self.logger.info("STEP 5: Generating Schema Comparisons")
        self.logger.info("=" * 50)

        try:
            # Import here to avoid circular imports
            from generate_web_comparisons import generate_comparison_matrix, get_recent_tags_and_commits

            # Get recent versions
            self.logger.info("Getting recent git versions...")
            versions = get_recent_tags_and_commits(limit=15)
            self.logger.info(f"Found {len(versions)} versions for comparison")

            # Generate comparisons
            output_dir = self.config.get("comparisons", {}).get("output_dir", "docs/data")
            self.logger.info(f"Generating comparisons to {output_dir}...")

            comparisons = generate_comparison_matrix(versions, output_dir)

            self.logger.info(f"Generated {len(comparisons)} comparison files")

            # Log some statistics
            with_changes = sum(1 for comp in comparisons if comp["has_changes"])
            self.logger.info(f"  - {with_changes} comparisons with changes")
            self.logger.info(f"  - {len(comparisons) - with_changes} comparisons with no changes")

            self.report["steps"].append({
                "step": "generate_comparisons",
                "status": "success",
                "details": {
                    "versions_processed": len(versions),
                    "comparisons_generated": len(comparisons),
                    "comparisons_with_changes": with_changes
                }
            })

            return True

        except ImportError as e:
            self.logger.error(f"Could not import comparison modules: {e}")
            self.logger.info("Skipping comparison generation")
            return True  # Don't fail the pipeline for this

        except Exception as e:
            self.logger.error(f"Comparison generation failed: {e}")
            self.report["issues"].append(f"Comparison generation failed: {e}")

            # Don't fail the pipeline for comparison issues
            self.logger.info("Continuing despite comparison generation failure")
            return True

    def run(self, csv_file_path: str = None) -> bool:
        """Run the complete update pipeline."""
        steps = [
            (self.step1_get_data, csv_file_path),
            (self.step2_convert_data, None),
            (self.step3_validate_schemas, None),
            (self.step4_generate_report, None),
            (self.step5_generate_comparisons, None)
        ]

        for step_func, param in steps:
            if param is not None:
                success = step_func(param)
            else:
                success = step_func()

            if not success and step_func.__name__ != 'step4_generate_report':
                self.step4_generate_report()  # Always generate report
                return False

        return self.report["success"]


def main():
    parser = argparse.ArgumentParser(description="Simple automated HBCD LORIS to ReproSchema update")
    parser.add_argument("--config", default="config/pipeline.yml", help="Configuration file path")
    parser.add_argument("--csv-file", help="Path to specific CSV file to use (optional)")
    args = parser.parse_args()

    pipeline = UpdatePipeline(args.config)
    success = pipeline.run(csv_file_path=args.csv_file)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
