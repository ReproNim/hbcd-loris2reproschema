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


def check_dependencies():
    """Check if all required Python packages are installed."""
    required_packages = [
        'pandas', 'yaml', 'bs4', 'requests'
    ]

    missing = []
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing.append(package)

    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    return True


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
    env_vars = ['LORIS_USER', 'LORIS_PASS']

    print("\nEnvironment variables (optional for local testing):")
    for var in env_vars:
        if os.environ.get(var):
            print(f"✅ {var} is set")
        else:
            print(f"⚠️  {var} is not set (ok for local testing)")


def test_script_syntax():
    """Test that the main script has valid syntax."""
    try:
        result = subprocess.run([
            sys.executable, '-m', 'py_compile', 'scripts/automated_update.py'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ scripts/automated_update.py syntax is valid")
            return True
        else:
            print("❌ scripts/automated_update.py has syntax errors:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error checking syntax: {e}")
        return False


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
