#!/usr/bin/env python3
"""
Simple ReproSchema comparison tool for HBCD project.
Focuses on semantic, human-readable changes rather than raw JSON diffs.
"""

import json
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import argparse


@dataclass
class ItemChange:
    """Represents a change to a single item/question."""
    name: str
    change_type: str  # 'added', 'removed', 'modified'
    description: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


@dataclass
class ActivityChange:
    """Represents changes to an activity/instrument."""
    name: str
    change_type: str  # 'added', 'removed', 'modified'
    added_items: List[str]
    removed_items: List[str]
    modified_items: List[ItemChange]

    @property
    def total_changes(self) -> int:
        return len(self.added_items) + len(self.removed_items) + len(self.modified_items)


@dataclass
class ComparisonReport:
    """Complete comparison between two schema versions."""
    from_version: str
    to_version: str
    summary: str
    activities: Dict[str, ActivityChange]

    @property
    def total_activities_changed(self) -> int:
        return len([a for a in self.activities.values() if a.total_changes > 0])

    @property
    def total_items_added(self) -> int:
        return sum(len(a.added_items) for a in self.activities.values())

    @property
    def total_items_removed(self) -> int:
        return sum(len(a.removed_items) for a in self.activities.values())

    @property
    def total_items_modified(self) -> int:
        return sum(len(a.modified_items) for a in self.activities.values())

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation suitable for JSON serialization."""
        report_dict = asdict(self)
        report_dict['statistics'] = {
            'activities_changed': self.total_activities_changed,
            'items_added': self.total_items_added,
            'items_removed': self.total_items_removed,
            'items_modified': self.total_items_modified
        }
        return report_dict


class SchemaComparator:
    """Compares ReproSchema versions with git integration."""

    # Path structure constants
    ACTIVITY_NAME_PATH_INDEX = 3  # reproschema_output/HBCD_LORIS/activities/ACTIVITY_NAME/...

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.schema_base_path = "reproschema_output/HBCD_LORIS"

    @staticmethod
    def _get_en(value):
        """Return plain string from localized or raw value."""
        if isinstance(value, dict):
            return value.get("en", next(iter(value.values()), ""))
        return value if value is not None else ""

    def read_schemas_from_git(self, git_ref: str) -> Dict[str, Any]:
        """Read all activity schemas and item files from a specific git reference."""
        schemas = {}

        try:
            # List all files under schema base path at the given ref
            result = subprocess.run([
                "git", "ls-tree", "-r", "--name-only", git_ref, self.schema_base_path
            ], capture_output=True, text=True, cwd=self.repo_path, check=True)

            all_files = [f for f in result.stdout.strip().split('\n') if f]
            # Include activity schemas (end with _schema) and item files under items/
            schema_files = [
                f for f in all_files
                if f.endswith('_schema') or "/items/" in f
            ]

            for file_path in schema_files:
                try:
                    file_content = subprocess.run([
                        "git", "show", f"{git_ref}:{file_path}"
                    ], capture_output=True, text=True, cwd=self.repo_path, check=True)

                    # All schema and item files are JSON (without extension)
                    schemas[file_path] = json.loads(file_content.stdout)
                except (json.JSONDecodeError, subprocess.CalledProcessError) as e:
                    print(f"Warning: Could not read or parse {file_path}: {e}", file=sys.stderr)
                    continue

        except subprocess.CalledProcessError as e:
            raise ValueError(f"Git operation failed for ref '{git_ref}': {e.stderr}") from e

        return schemas

    def extract_human_readable_info(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract human-readable information from a schema."""
        category = schema.get('category', '')
        is_activity = category == 'reproschema:Activity'
        is_item = category == 'reproschema:Item'

        info = {
            'name': schema.get('id', 'Unknown'),
            'title': self._get_en(schema.get('prefLabel', 'Unknown')),
            'description': self._get_en(schema.get('description', '')),
            'type': 'activity' if is_activity else ('item' if is_item else 'unknown')
        }

        if is_activity:
            ui_order = schema.get('ui', {}).get('order', [])
            info['items'] = [item.split('/')[-1] for item in ui_order if isinstance(item, str)]
        elif is_item:
            info['question'] = self._get_en(schema.get('question', ''))
            info['input_type'] = schema.get('ui', {}).get('inputType', '')
            choices = schema.get('responseOptions', {}).get('choices', [])
            # Use human-friendly values for comparison; fall back to names if value missing
            normalized_choices = []
            for ch in choices:
                val = ch.get('value')
                name = ch.get('name')
                normalized_choices.append(self._get_en(val) if val is not None else self._get_en(name))
            info['choices'] = normalized_choices

        return info

    def compare_versions(self, from_ref: str, to_ref: str) -> ComparisonReport:
        """Compare two schema versions and generate human-readable report."""

        print(f"Comparing {from_ref} → {to_ref}")

        # Read schemas from both versions
        old_schemas = self.read_schemas_from_git(from_ref)
        new_schemas = self.read_schemas_from_git(to_ref)

        print(f"Found {len(old_schemas)} schemas in {from_ref}")
        print(f"Found {len(new_schemas)} schemas in {to_ref}")

        # Process schemas into comparable format
        old_activities = self._group_schemas_by_activity(old_schemas)
        new_activities = self._group_schemas_by_activity(new_schemas)

        # Compare activities
        activity_changes = {}
        all_activity_names = set(old_activities.keys()) | set(new_activities.keys())

        for activity_name in all_activity_names:
            old_activity = old_activities.get(activity_name, {})
            new_activity = new_activities.get(activity_name, {})

            change = self._compare_activity(activity_name, old_activity, new_activity)
            if change.total_changes > 0:
                activity_changes[activity_name] = change

        # Generate summary
        report = ComparisonReport(
            from_version=from_ref,
            to_version=to_ref,
            summary=self._generate_summary(activity_changes),
            activities=activity_changes
        )

        return report

    def _group_schemas_by_activity(self, schemas: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Group schemas by activity name."""
        activities = {}

        for file_path, schema in schemas.items():
            info = self.extract_human_readable_info(schema)

            # Derive activity name from path for stability
            path_parts = file_path.split('/')
            activity_name = path_parts[self.ACTIVITY_NAME_PATH_INDEX] if len(path_parts) > self.ACTIVITY_NAME_PATH_INDEX else None

            if info['type'] == 'activity' and activity_name:
                activities[activity_name] = {
                    'info': {'name': activity_name, 'title': info.get('title', activity_name)},
                    'items': {}
                }
            elif info['type'] == 'item' and activity_name:
                if activity_name not in activities:
                    activities[activity_name] = {'info': {'name': activity_name}, 'items': {}}
                # Use item id as key
                item_id = info['name']
                activities[activity_name]['items'][item_id] = info

        return activities

    def _compare_activity(self, name: str, old: Dict[str, Any], new: Dict[str, Any]) -> ActivityChange:
        """Compare a single activity between versions."""

        if not old:  # New activity
            return ActivityChange(
                name=name,
                change_type='added',
                added_items=list(new.get('items', {}).keys()),
                removed_items=[],
                modified_items=[]
            )

        if not new:  # Removed activity
            return ActivityChange(
                name=name,
                change_type='removed',
                added_items=[],
                removed_items=list(old.get('items', {}).keys()),
                modified_items=[]
            )

        # Compare items within activity
        old_items = old.get('items', {})
        new_items = new.get('items', {})

        old_item_names = set(old_items.keys())
        new_item_names = set(new_items.keys())

        added_items = list(new_item_names - old_item_names)
        removed_items = list(old_item_names - new_item_names)
        common_items = old_item_names & new_item_names

        modified_items = []
        for item_name in common_items:
            old_item = old_items[item_name]
            new_item = new_items[item_name]

            changes = self._compare_item(item_name, old_item, new_item)
            if changes:
                modified_items.extend(changes)

        change_type = 'modified' if (added_items or removed_items or modified_items) else 'unchanged'

        return ActivityChange(
            name=name,
            change_type=change_type,
            added_items=added_items,
            removed_items=removed_items,
            modified_items=modified_items
        )

    def _compare_item(self, name: str, old: Dict[str, Any], new: Dict[str, Any]) -> List[ItemChange]:
        """Compare a single item and return list of changes."""
        changes = []

        # Compare question text
        old_question = old.get('question', '')
        new_question = new.get('question', '')
        if old_question != new_question:
            changes.append(ItemChange(
                name=name,
                change_type='modified',
                description=f"Question text changed",
                old_value=old_question[:100] + "..." if len(old_question) > 100 else old_question,
                new_value=new_question[:100] + "..." if len(new_question) > 100 else new_question
            ))

        # Compare response options
        old_choices = old.get('choices', [])
        new_choices = new.get('choices', [])
        if old_choices != new_choices:
            changes.append(ItemChange(
                name=name,
                change_type='modified',
                description=f"Response options changed",
                old_value=str(old_choices),
                new_value=str(new_choices)
            ))

        return changes

    def _generate_summary(self, activity_changes: Dict[str, ActivityChange]) -> str:
        """Generate a human-readable summary of all changes."""
        if not activity_changes:
            return "No changes detected"

        total_added = sum(len(a.added_items) for a in activity_changes.values())
        total_removed = sum(len(a.removed_items) for a in activity_changes.values())
        total_modified = sum(len(a.modified_items) for a in activity_changes.values())

        parts = []
        if total_added:
            parts.append(f"Added {total_added} items")
        if total_removed:
            parts.append(f"Removed {total_removed} items")
        if total_modified:
            parts.append(f"Modified {total_modified} items")

        activities_changed = len(activity_changes)
        parts.append(f"across {activities_changed} activities")

        return ", ".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Compare ReproSchema versions")
    parser.add_argument("--from", dest="from_ref", required=True, help="Git reference for old version")
    parser.add_argument("--to", dest="to_ref", required=True, help="Git reference for new version")
    parser.add_argument("--output", help="Output file for JSON report")
    parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format")

    args = parser.parse_args()

    comparator = SchemaComparator()

    try:
        report = comparator.compare_versions(args.from_ref, args.to_ref)

        if args.format == "json":
            # Convert dataclasses to dict for JSON serialization
            report_dict = report.to_dict()

            output = json.dumps(report_dict, indent=2)
        else:
            # Text format
            output = f"Schema Comparison: {report.from_version} → {report.to_version}\n"
            output += f"Summary: {report.summary}\n\n"

            for name, activity in report.activities.items():
                output += f"Activity: {name}\n"
                if activity.added_items:
                    output += f"  + Added items: {', '.join(activity.added_items)}\n"
                if activity.removed_items:
                    output += f"  - Removed items: {', '.join(activity.removed_items)}\n"
                if activity.modified_items:
                    output += f"  ~ Modified items:\n"
                    for item in activity.modified_items:
                        output += f"    {item.name}: {item.description}\n"
                output += "\n"

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Report saved to {args.output}")
        else:
            print(output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
