#!/usr/bin/env python3
"""
Generate comparison JSON files for the web interface.
This script creates comparisons between recent versions and saves them as JSON files
that can be served by GitHub Pages.
"""

import itertools
import json
import subprocess
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from schema_comparison import SchemaComparator


def get_git_tags(limit=20):
    """Get git tags only; optionally limit returned list for pair generation."""
    try:
        result = subprocess.run(["git", "tag", "--sort=-version:refname"], capture_output=True, text=True, check=True)
        tags = [t for t in result.stdout.strip().split("\n") if t]
        return tags if limit is None else tags[:limit]
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not get git tags: {e}")
        return []


def generate_comparison_matrix(versions, output_dir):
    """Generate comparison files between version pairs."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    comparator = SchemaComparator()
    generated_files = []

    # Generate comparisons for all unique pairs of versions
    # Assuming versions are sorted newest to oldest, we want pairs (older, newer).
    # itertools.combinations on the reversed list gives us that.
    for from_version, to_version in itertools.combinations(reversed(versions), 2):

        try:
            print(f"Generating comparison: {from_version} → {to_version}")

            report = comparator.compare_versions(from_version, to_version)

            # Convert to JSON-serializable format
            report_dict = report.to_dict()

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
    # Expose ALL tags for the website to list, even if we didn't generate all pairs
    all_tags = get_git_tags(limit=None)
    index_data = {
        'generated_at': datetime.now().isoformat(),
        'available_versions': all_tags,
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

    # Replace the availableVersions array using robust comment markers
    start_marker = "// START_VERSIONS"
    end_marker = "// END_VERSIONS"

    start_idx = html_content.find(start_marker)
    if start_idx == -1:
        print("Warning: Could not find START_VERSIONS marker in HTML")
        return

    end_idx = html_content.find(end_marker, start_idx)
    if end_idx == -1:
        print("Warning: Could not find END_VERSIONS marker in HTML")
        return

    # Replace the section between markers
    new_section = f"{start_marker}\n            const availableVersions = {versions_js};\n            {end_marker}"
    new_html = html_content[:start_idx] + new_section + html_content[end_idx + len(end_marker):]

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
    versions = get_git_tags(args.limit)
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
