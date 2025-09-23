#!/usr/bin/env python3
"""
Smart Change Detection for HBCD Data Dictionary

Compares new and existing data dictionaries with configurable thresholds
and generates detailed comparison logs.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

import pandas as pd
import yaml


class DataDictionaryComparator:
    """Intelligent comparison of HBCD data dictionaries."""

    def __init__(self, config_path: str = "config/change_detection.yml"):
        """Initialize comparator with configuration."""
        self.config = self._load_config(config_path)
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Setup logging
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / f"change_detection_{self.timestamp}.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Initialize comparison results
        self.comparison_report = {
            "timestamp": self.timestamp,
            "files_compared": {},
            "summary": {},
            "detailed_changes": {},
            "decision": {
                "trigger_conversion": False,
                "reason": "",
                "thresholds_met": []
            }
        }

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            # Create default config
            default_config = {
                "change_detection": {
                    "ignore_columns": [
                        "data_dict_id",
                        "export_date",
                        "export_timestamp",
                        "created_date",
                        "modified_date",
                        "last_updated"
                    ],
                    "thresholds": {
                        "min_field_changes": 3,
                        "min_new_instruments": 1,
                        "min_modified_instruments": 2,
                        "min_deleted_instruments": 1,
                        "min_choice_changes": 5,
                        "significant_change_percentage": 1.0
                    },
                    "ignore_whitespace": True,
                    "ignore_case": True,
                    "ignore_order": False,
                    "key_columns": [
                        "full_instrument_name",
                        "name",
                        "field_type"
                    ],
                    "significant_columns": [
                        "field_type",
                        "loris_required",
                        "option_values",
                        "question",
                        "redcap_branching_logic"
                    ]
                }
            }

            with open(config_file, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False)

            print(f"Created default config at {config_path}")
            return default_config

        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def _normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize data for comparison."""
        config = self.config["change_detection"]

        # Drop ignored columns
        columns_to_drop = [col for col in config["ignore_columns"] if col in df.columns]
        if columns_to_drop:
            df = df.drop(columns=columns_to_drop)
            self.logger.info(f"Dropped ignored columns: {columns_to_drop}")

        # Normalize whitespace
        if config["ignore_whitespace"]:
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).str.strip()

        # Normalize case
        if config["ignore_case"]:
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).str.lower()

        # Sort by key columns if ignore_order is True
        if config["ignore_order"] and all(col in df.columns for col in config["key_columns"]):
            df = df.sort_values(config["key_columns"]).reset_index(drop=True)

        return df

    def _compare_instruments(self, old_df: pd.DataFrame, new_df: pd.DataFrame) -> Dict[str, Any]:
        """Compare instruments between datasets."""
        old_instruments = set(old_df['full_instrument_name'].unique())
        new_instruments = set(new_df['full_instrument_name'].unique())

        added = new_instruments - old_instruments
        removed = old_instruments - new_instruments
        common = old_instruments & new_instruments

        # Check for modified instruments
        modified = set()
        for instrument in common:
            old_inst = old_df[old_df['full_instrument_name'] == instrument]
            new_inst = new_df[new_df['full_instrument_name'] == instrument]

            # Compare significant columns only
            sig_columns = [col for col in self.config["change_detection"]["significant_columns"]
                          if col in old_inst.columns and col in new_inst.columns]

            if not old_inst[sig_columns].equals(new_inst[sig_columns]):
                modified.add(instrument)

        return {
            "added_instruments": list(added),
            "removed_instruments": list(removed),
            "modified_instruments": list(modified),
            "total_instruments_old": len(old_instruments),
            "total_instruments_new": len(new_instruments)
        }

    def _compare_fields(self, old_df: pd.DataFrame, new_df: pd.DataFrame) -> Dict[str, Any]:
        """Compare individual fields between datasets."""
        # Determine the field name column (could be 'field_name' or 'name')
        field_name_col = 'field_name' if 'field_name' in old_df.columns else 'name'

        if field_name_col not in old_df.columns or field_name_col not in new_df.columns:
            self.logger.error(f"Required column '{field_name_col}' not found in data")
            return {
                "added_fields": [],
                "removed_fields": [],
                "modified_fields": [],
                "choice_changes": 0,
                "total_fields_old": 0,
                "total_fields_new": 0
            }

        # Create unique field identifiers
        old_df['field_id'] = old_df['full_instrument_name'] + '::' + old_df[field_name_col]
        new_df['field_id'] = new_df['full_instrument_name'] + '::' + new_df[field_name_col]

        old_fields = set(old_df['field_id'])
        new_fields = set(new_df['field_id'])

        added_fields = new_fields - old_fields
        removed_fields = old_fields - new_fields
        common_fields = old_fields & new_fields

        # Check for modified fields
        modified_fields = []
        choice_changes = 0

        sig_columns = [col for col in self.config["change_detection"]["significant_columns"]
                      if col in old_df.columns and col in new_df.columns]

        for field_id in common_fields:
            old_field = old_df[old_df['field_id'] == field_id].iloc[0]
            new_field = new_df[new_df['field_id'] == field_id].iloc[0]

            changes = {}
            for col in sig_columns:
                if str(old_field[col]) != str(new_field[col]):
                    changes[col] = {
                        "old": str(old_field[col]),
                        "new": str(new_field[col])
                    }

                    # Count choice changes specially
                    if col == 'choices' and old_field[col] != new_field[col]:
                        choice_changes += 1

            if changes:
                modified_fields.append({
                    "field_id": field_id,
                    "changes": changes
                })

        return {
            "added_fields": list(added_fields),
            "removed_fields": list(removed_fields),
            "modified_fields": modified_fields,
            "choice_changes": choice_changes,
            "total_fields_old": len(old_fields),
            "total_fields_new": len(new_fields)
        }

    def _evaluate_thresholds(self, instrument_changes: Dict, field_changes: Dict) -> Tuple[bool, List[str]]:
        """Evaluate if changes meet configured thresholds."""
        thresholds = self.config["change_detection"]["thresholds"]
        met_thresholds = []

        # Check individual thresholds
        if len(instrument_changes["added_instruments"]) >= thresholds["min_new_instruments"]:
            met_thresholds.append(f"New instruments: {len(instrument_changes['added_instruments'])} >= {thresholds['min_new_instruments']}")

        if len(instrument_changes["removed_instruments"]) >= thresholds["min_deleted_instruments"]:
            met_thresholds.append(f"Deleted instruments: {len(instrument_changes['removed_instruments'])} >= {thresholds['min_deleted_instruments']}")

        if len(instrument_changes["modified_instruments"]) >= thresholds["min_modified_instruments"]:
            met_thresholds.append(f"Modified instruments: {len(instrument_changes['modified_instruments'])} >= {thresholds['min_modified_instruments']}")

        if len(field_changes["modified_fields"]) >= thresholds["min_field_changes"]:
            met_thresholds.append(f"Modified fields: {len(field_changes['modified_fields'])} >= {thresholds['min_field_changes']}")

        if field_changes["choice_changes"] >= thresholds["min_choice_changes"]:
            met_thresholds.append(f"Choice changes: {field_changes['choice_changes']} >= {thresholds['min_choice_changes']}")

        # Check percentage threshold
        total_old = field_changes["total_fields_old"]
        total_changes = len(field_changes["added_fields"]) + len(field_changes["removed_fields"]) + len(field_changes["modified_fields"])
        change_percentage = (total_changes / total_old * 100) if total_old > 0 else 0

        if change_percentage >= thresholds["significant_change_percentage"]:
            met_thresholds.append(f"Change percentage: {change_percentage:.2f}% >= {thresholds['significant_change_percentage']}%")

        # Decision: trigger if any threshold is met
        trigger_conversion = len(met_thresholds) > 0

        return trigger_conversion, met_thresholds

    def compare_files(self, old_file: str, new_file: str) -> bool:
        """Compare two data dictionary files and decide if conversion should be triggered."""
        self.logger.info(f"Comparing {old_file} with {new_file}")

        # Record file paths
        self.comparison_report["files_compared"] = {
            "old_file": old_file,
            "new_file": new_file
        }

        try:
            # Load and normalize data
            old_df = pd.read_csv(old_file)
            new_df = pd.read_csv(new_file)

            self.logger.info(f"Loaded {len(old_df)} rows from old file, {len(new_df)} rows from new file")

            old_df_norm = self._normalize_data(old_df.copy())
            new_df_norm = self._normalize_data(new_df.copy())

            # Compare instruments
            instrument_changes = self._compare_instruments(old_df_norm, new_df_norm)
            self.logger.info(f"Instrument analysis: {len(instrument_changes['added_instruments'])} added, "
                           f"{len(instrument_changes['removed_instruments'])} removed, "
                           f"{len(instrument_changes['modified_instruments'])} modified")

            # Compare fields
            field_changes = self._compare_fields(old_df_norm, new_df_norm)
            self.logger.info(f"Field analysis: {len(field_changes['added_fields'])} added, "
                           f"{len(field_changes['removed_fields'])} removed, "
                           f"{len(field_changes['modified_fields'])} modified")

            # Evaluate thresholds
            trigger_conversion, met_thresholds = self._evaluate_thresholds(instrument_changes, field_changes)

            # Update report
            self.comparison_report["summary"] = {
                "instruments": instrument_changes,
                "fields": field_changes
            }
            self.comparison_report["detailed_changes"] = {
                "instrument_details": instrument_changes,
                "field_details": field_changes
            }
            self.comparison_report["decision"] = {
                "trigger_conversion": trigger_conversion,
                "reason": "Thresholds met" if trigger_conversion else "No significant changes detected",
                "thresholds_met": met_thresholds
            }

            # Log decision
            if trigger_conversion:
                self.logger.info(f"🚀 TRIGGERING CONVERSION - Thresholds met: {met_thresholds}")
            else:
                self.logger.info("✅ No conversion needed - Changes below threshold")

            return trigger_conversion

        except Exception as e:
            self.logger.error(f"Error during comparison: {e}")
            self.comparison_report["decision"] = {
                "trigger_conversion": False,
                "reason": f"Comparison failed: {e}",
                "thresholds_met": []
            }
            return False

    def save_report(self, output_path: str = None) -> str:
        """Save detailed comparison report."""
        if output_path is None:
            output_path = f"logs/comparison_report_{self.timestamp}.json"

        with open(output_path, 'w') as f:
            json.dump(self.comparison_report, f, indent=2, default=str)

        self.logger.info(f"Comparison report saved to {output_path}")
        return output_path


def main():
    parser = argparse.ArgumentParser(description="Detect meaningful changes in HBCD data dictionary")
    parser.add_argument("--old-file", required=True, help="Path to previous data dictionary CSV")
    parser.add_argument("--new-file", required=True, help="Path to new data dictionary CSV")
    parser.add_argument("--config", default="config/change_detection.yml", help="Configuration file")
    parser.add_argument("--output-report", help="Output path for comparison report")
    parser.add_argument("--quiet", action="store_true", help="Suppress output except for decision")

    args = parser.parse_args()

    # Validate files exist
    if not Path(args.old_file).exists():
        print(f"Error: Old file not found: {args.old_file}")
        sys.exit(1)

    if not Path(args.new_file).exists():
        print(f"Error: New file not found: {args.new_file}")
        sys.exit(1)

    # Compare files
    comparator = DataDictionaryComparator(args.config)
    trigger_conversion = comparator.compare_files(args.old_file, args.new_file)

    # Save report
    report_path = comparator.save_report(args.output_report)

    # Output decision for CI consumption
    if args.quiet:
        print("true" if trigger_conversion else "false")
    else:
        print(f"Trigger conversion: {trigger_conversion}")
        print(f"Report saved to: {report_path}")

    # Exit with appropriate code
    sys.exit(0 if trigger_conversion else 1)


if __name__ == "__main__":
    main()
