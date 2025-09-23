#!/usr/bin/env python3
"""
Simple ReproSchema comparison tool for HBCD project.
Focuses on semantic, human-readable changes rather than raw JSON diffs.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
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


class SchemaComparator:
    """Compares ReproSchema versions with git integration."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.schema_base_path = "reproschema_output/HBCD_LORIS"

    def read_schemas_from_git(self, git_ref: str) -> Dict[str, Any]:
        """Read all schema files from a specific git reference."""
        schemas = {}

        # Get list of schema files from git
        try:
            result = subprocess.run([
                "git", "ls-tree", "-r", "--name-only", git_ref, self.schema_base_path
            ], capture_output=True, text=True, cwd=self.repo_path)

            if result.returncode != 0:
                raise ValueError(f"Failed to list files for git ref {git_ref}: {result.stderr}")

            schema_files = [f for f in result.stdout.strip().split('\n')
                          if f.endswith('_schema') and f]

            # Read each schema file
            for file_path in schema_files:
                try:
                    file_content = subprocess.run([
                        "git", "show", f"{git_ref}:{file_path}"
                    ], capture_output=True, text=True, cwd=self.repo_path)

                    if file_content.returncode == 0:
                        schemas[file_path] = json.loads(file_content.stdout)
                except (json.JSONDecodeError, subprocess.CalledProcessError):
                    # Skip files that can't be read or parsed
                    continue

        except subprocess.CalledProcessError as e:
            raise ValueError(f"Git operation failed: {e}")

        return schemas

    def extract_human_readable_info(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract human-readable information from a schema."""
        info = {
            'name': schema.get('@id', 'Unknown'),
            'title': schema.get('prefLabel', 'Unknown'),
            'description': schema.get('description', ''),
            'type': 'activity' if 'ui' in schema else 'item'
        }

        # For activities, get the item list
        if info['type'] == 'activity':
            ui_order = schema.get('ui', {}).get('order', [])
            info['items'] = [item.split('/')[-1] for item in ui_order if isinstance(item, str)]

        # For items, get question text and response options
        elif info['type'] == 'item':
            info['question'] = schema.get('question', '')
            response_options = schema.get('responseOptions', {})
            if 'choices' in response_options:
                info['choices'] = [choice.get('name', '') for choice in response_options['choices']]
            info['input_type'] = response_options.get('inputType', '')

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

            if info['type'] == 'activity':
                activity_name = info['name']
                activities[activity_name] = {
                    'info': info,
                    'items': {}
                }
            elif info['type'] == 'item':
                # Extract activity name from file path
                path_parts = file_path.split('/')
                if len(path_parts) >= 4:  # reproschema_output/HBCD_LORIS/activities/ACTIVITY_NAME/items/ITEM
                    activity_name = path_parts[3]
                    if activity_name not in activities:
                        activities[activity_name] = {'info': {'name': activity_name}, 'items': {}}
                    activities[activity_name]['items'][info['name']] = info

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
            report_dict = {
                'from_version': report.from_version,
                'to_version': report.to_version,
                'summary': report.summary,
                'statistics': {
                    'activities_changed': report.total_activities_changed,
                    'items_added': report.total_items_added,
                    'items_removed': report.total_items_removed,
                    'items_modified': report.total_items_modified
                },
                'activities': {
                    name: {
                        'change_type': activity.change_type,
                        'added_items': activity.added_items,
                        'removed_items': activity.removed_items,
                        'modified_items': [
                            {
                                'name': item.name,
                                'change_type': item.change_type,
                                'description': item.description,
                                'old_value': item.old_value,
                                'new_value': item.new_value
                            }
                            for item in activity.modified_items
                        ]
                    }
                    for name, activity in report.activities.items()
                }
            }

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
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
