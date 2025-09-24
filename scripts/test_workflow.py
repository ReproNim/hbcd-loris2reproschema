#!/usr/bin/env python3
"""
Test script for validating the automated workflow locally.

This script helps identify common issues that might cause CI/CD failures.
"""

import os
import sys
import subprocess
import importlib
from pathlib import Path
try:
    import importlib.metadata as importlib_metadata
except ImportError:
    # Fallback for Python < 3.8
    import importlib_metadata

try:
    from packaging.version import parse as parse_version
except ImportError:
    parse_version = None


def check_dependencies():
    """Check if all required Python packages are installed with correct versions."""
    # Mapping of import names to package names and minimum versions
    # Security fix: Use correct package names to avoid malicious packages
    required_packages = {
        'pandas': {'package': 'pandas', 'min_version': '1.5.0'},
        'yaml': {'package': 'PyYAML', 'min_version': '6.0'},  # Security: use PyYAML not yaml
        'bs4': {'package': 'beautifulsoup4', 'min_version': '4.11.0'},
        'requests': {'package': 'requests', 'min_version': '2.28.0'}
    }

    missing = []
    version_issues = []

    for import_name, pkg_info in required_packages.items():
        try:
            # Check if package can be imported
            importlib.import_module(import_name)

            # Check version if available
            try:
                installed_version = importlib_metadata.version(pkg_info['package'])
                if _version_compare(installed_version, pkg_info['min_version']) < 0:
                    print(f"⚠️  {import_name} (v{installed_version} < {pkg_info['min_version']})")
                    version_issues.append(f"{pkg_info['package']}>={pkg_info['min_version']}")
                else:
                    print(f"✅ {import_name} (v{installed_version})")
            except importlib_metadata.PackageNotFoundError:
                print(f"✅ {import_name} (version check skipped: package metadata not found)")

        except ImportError:
            print(f"❌ {import_name}")
            missing.append(pkg_info['package'])

    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))

    if version_issues:
        print(f"\nVersion issues: {', '.join(version_issues)}")
        print("Upgrade with: pip install --upgrade " + " ".join(version_issues))

    return len(missing) == 0 and len(version_issues) == 0


def _version_compare(version1, version2):
    """Compares two version strings using the 'packaging' library if available.

    Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2.
    """
    if parse_version:
        # Use packaging library for robust version comparison
        v1_parsed = parse_version(version1)
        v2_parsed = parse_version(version2)

        if v1_parsed < v2_parsed:
            return -1
        elif v1_parsed > v2_parsed:
            return 1
        else:
            return 0
    else:
        # Fallback to simple comparison if packaging not available
        def normalize(v):
            return [int(x) for x in v.split('.')]

        try:
            v1_parts = normalize(version1)
            v2_parts = normalize(version2)

            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))

            if v1_parts < v2_parts:
                return -1
            elif v1_parts > v2_parts:
                return 1
            else:
                return 0
        except ValueError:
            # If version parsing fails, assume they're equal
            return 0


def check_files():
    """Check if required configuration files exist."""
    required_files = [
        'config/pipeline.yml',
        'config/conversion.yml',
        'scripts/automated_update.py',
        'scripts/loris2reproschema.py'
    ]

    missing = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            missing.append(file_path)

    if missing:
        print(f"\nMissing files: {', '.join(missing)}")
        return False
    return True


def check_environment():
    """Check environment variables (optional for local testing)."""
    env_vars = ['HBCD_USERNAME', 'HBCD_PASSWORD']

    print("\nEnvironment variables (optional for local testing):")
    for var in env_vars:
        if os.environ.get(var):
            print(f"✅ {var} is set")
        else:
            print(f"⚠️  {var} is not set (ok for local testing)")


def test_script_syntax():
    """Test that all relevant scripts have valid syntax."""
    # Comprehensive script validation as recommended by Gemini
    scripts_to_check = [
        'scripts/automated_update.py',
        'scripts/loris2reproschema.py',
        'scripts/retrieve_script.py'
    ]

    all_valid = True
    for script in scripts_to_check:
        if not Path(script).exists():
            print(f"⚠️  {script} not found (skipping syntax check)")
            continue

        try:
            result = subprocess.run([
                sys.executable, '-m', 'py_compile', script
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ {script} syntax is valid")
            else:
                print(f"❌ {script} has syntax errors:")
                print(result.stderr)
                all_valid = False
        except OSError as e:
            print(f"❌ Error checking {script} syntax: {e}")
            all_valid = False

    return all_valid


def main():
    """Run all checks."""
    print("🔍 Testing Workflow Components\n")

    checks = [
        ("Dependencies", check_dependencies),
        ("Required Files", check_files),
        ("Script Syntax", test_script_syntax),
    ]

    all_passed = True
    for name, check_func in checks:
        print(f"\n📋 Checking {name}:")
        if not check_func():
            all_passed = False

    # Environment check (informational only)
    check_environment()

    print("\n" + "="*50)
    if all_passed:
        print("✅ All checks passed! The workflow should work in CI/CD.")
    else:
        print("❌ Some checks failed. Fix the issues before deploying.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
