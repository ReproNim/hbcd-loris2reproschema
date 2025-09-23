#!/usr/bin/env python3
"""
Generate comparison JSON files for the web interface.
This script creates comparisons between recent versions and saves them as JSON files
that can be served by GitHub Pages.
"""

import json
import os
import subprocess
from pathlib import Path
from schema_comparison import SchemaComparator


def get_recent_tags_and_commits(limit=20):
    """Get recent git tags and commits for comparison."""
    versions = []

    try:
        # Get recent tags
        result = subprocess.run([
            "git", "tag", "--sort=-version:refname"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            tags = result.stdout.strip().split('\n')
            versions.extend([tag for tag in tags if tag][:10])  # Last 10 tags

        # Get recent commits
        result = subprocess.run([
            "git", "log", "--oneline", "--format=%H", f"-{limit}"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            commits = result.stdout.strip().split('\n')
            versions.extend([commit[:8] for commit in commits if commit][:10])  # Last 10 commits (short)

        # Add some common references
        versions.extend(['HEAD', 'main'])

    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not get git history: {e}")
        # Fallback to basic references
        versions = ['HEAD', 'HEAD~1', 'HEAD~2', 'HEAD~3', 'main']

    return list(dict.fromkeys(versions))  # Remove duplicates while preserving order


def generate_comparison_matrix(versions, output_dir):
    """Generate comparison files between version pairs."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    comparator = SchemaComparator()
    generated_files = []

    # Generate comparisons between consecutive versions
    for i in range(len(versions) - 1):
        from_version = versions[i + 1]  # Older version
        to_version = versions[i]       # Newer version

        try:
            print(f"Generating comparison: {from_version} → {to_version}")

            report = comparator.compare_versions(from_version, to_version)

            # Convert to JSON-serializable format
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

            # Save as JSON file
            filename = f"{from_version}_to_{to_version}.json".replace('/', '_').replace('~', '_')
            filepath = output_dir / filename

            with open(filepath, 'w') as f:
                json.dump(report_dict, f, indent=2)

            generated_files.append({
                'filename': filename,
                'from_version': from_version,
                'to_version': to_version,
                'summary': report.summary,
                'has_changes': report.total_activities_changed > 0
            })

            print(f"  → Saved to {filename}")

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            continue

    # Generate index file with available comparisons
    index_data = {
        'generated_at': subprocess.run(['date', '-Iseconds'], capture_output=True, text=True).stdout.strip(),
        'available_versions': versions,
        'comparisons': generated_files
    }

    with open(output_dir / 'index.json', 'w') as f:
        json.dump(index_data, f, indent=2)

    print(f"\nGenerated {len(generated_files)} comparison files in {output_dir}")
    return generated_files


def update_html_versions(versions, html_file="docs/index.html"):
    """Update the HTML file with current version list."""

    html_path = Path(html_file)
    if not html_path.exists():
        print(f"Warning: HTML file {html_file} not found")
        return

    # Read current HTML
    with open(html_path, 'r') as f:
        html_content = f.read()

    # Generate JavaScript array
    versions_js = json.dumps(versions[:15], indent=12)  # Limit to 15 most recent

    # Replace the availableVersions array
    start_marker = "const availableVersions = ["
    end_marker = "];"

    start_idx = html_content.find(start_marker)
    if start_idx == -1:
        print("Warning: Could not find availableVersions array in HTML")
        return

    end_idx = html_content.find(end_marker, start_idx)
    if end_idx == -1:
        print("Warning: Could not find end of availableVersions array")
        return

    # Replace the array
    new_array = f"const availableVersions = {versions_js}"
    new_html = html_content[:start_idx] + new_array + html_content[end_idx + len(end_marker):]

    # Write back
    with open(html_path, 'w') as f:
        f.write(new_html)

    print(f"Updated {html_file} with {len(versions)} versions")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate web comparison files")
    parser.add_argument("--output-dir", default="docs/data", help="Output directory for JSON files")
    parser.add_argument("--update-html", action="store_true", help="Update HTML with current versions")
    parser.add_argument("--limit", type=int, default=20, help="Limit number of versions to process")

    args = parser.parse_args()

    print("Getting recent versions...")
    versions = get_recent_tags_and_commits(args.limit)
    print(f"Found {len(versions)} versions: {versions[:10]}{'...' if len(versions) > 10 else ''}")

    print("\nGenerating comparison files...")
    generate_comparison_matrix(versions, args.output_dir)

    if args.update_html:
        print("\nUpdating HTML file...")
        update_html_versions(versions)

    print("\n✅ Done! You can now:")
    print(f"   1. Open docs/index.html in a browser")
    print(f"   2. Check generated files in {args.output_dir}")
    print(f"   3. Commit and push to enable GitHub Pages")


if __name__ == "__main__":
    main()
