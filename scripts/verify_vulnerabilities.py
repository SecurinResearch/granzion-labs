#!/usr/bin/env python3
"""
Script to verify all intentional vulnerabilities are properly documented.

Checks that:
1. All vulnerabilities in catalog have code markers
2. All code markers reference catalog entries
3. Threat IDs are consistent
"""

import re
from pathlib import Path
from typing import Dict, List, Set

# Vulnerability catalog from VULNERABILITIES.md
CATALOG_VULNERABILITIES = {
    "IT-01", "IT-02", "IT-03", "IT-04", "IT-05", "IT-06",
    "M-01", "M-02", "M-03", "M-04", "M-05", "M-06",
    "T-01", "T-02", "T-03", "T-04", "T-05",
    "C-01", "C-02", "C-03", "C-04", "C-05",
    "O-01", "O-02", "O-03", "O-04",
    "A-01", "A-02", "A-03", "A-04",
    "IF-01", "IF-02", "IF-03", "IF-04", "IF-05",
    "V-01", "V-02", "V-03", "V-04", "V-05",
}


def find_vulnerability_markers(root_dir: Path) -> Dict[str, List[str]]:
    """Find all vulnerability markers in code."""
    markers = {}
    
    # Search in src/ and scenarios/
    for pattern in ["src/**/*.py", "scenarios/**/*.py"]:
        for file_path in root_dir.glob(pattern):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find all VULNERABILITY comments
            matches = re.findall(
                r'#\s*VULNERABILITY:?\s*([A-Z]{1,2}-\d{2}(?:,\s*[A-Z]{1,2}-\d{2})*)',
                content,
                re.IGNORECASE
            )
            
            for match in matches:
                # Split multiple threat IDs
                threat_ids = [tid.strip() for tid in match.split(',')]
                for threat_id in threat_ids:
                    if threat_id not in markers:
                        markers[threat_id] = []
                    markers[threat_id].append(str(file_path.relative_to(root_dir)))
    
    return markers


def verify_vulnerabilities(root_dir: Path):
    """Verify vulnerability documentation."""
    print("=" * 80)
    print("VULNERABILITY VERIFICATION REPORT")
    print("=" * 80)
    print()
    
    # Find all markers in code
    code_markers = find_vulnerability_markers(root_dir)
    
    # Check catalog completeness
    print("1. CATALOG COMPLETENESS")
    print("-" * 80)
    
    catalog_ids = set(CATALOG_VULNERABILITIES)
    code_ids = set(code_markers.keys())
    
    print(f"Vulnerabilities in catalog: {len(catalog_ids)}")
    print(f"Vulnerabilities in code:    {len(code_ids)}")
    print()
    
    # Vulnerabilities in catalog but not in code
    missing_in_code = catalog_ids - code_ids
    if missing_in_code:
        print(f"⚠️  Missing in code ({len(missing_in_code)}):")
        for vid in sorted(missing_in_code):
            print(f"   - {vid}")
        print()
    else:
        print("✓ All catalog vulnerabilities have code markers")
        print()
    
    # Vulnerabilities in code but not in catalog
    missing_in_catalog = code_ids - catalog_ids
    if missing_in_catalog:
        print(f"⚠️  Missing in catalog ({len(missing_in_catalog)}):")
        for vid in sorted(missing_in_catalog):
            print(f"   - {vid} (found in: {', '.join(code_markers[vid][:2])})")
        print()
    else:
        print("✓ All code markers are in catalog")
        print()
    
    # Show vulnerability distribution
    print("2. VULNERABILITY DISTRIBUTION")
    print("-" * 80)
    
    categories = {
        "IT": "Identity & Trust",
        "M": "Memory",
        "T": "Tool",
        "C": "Communication",
        "O": "Orchestration",
        "A": "Autonomy",
        "IF": "Infrastructure",
        "V": "Visibility",
    }
    
    for prefix, name in categories.items():
        count = sum(1 for vid in code_ids if vid.startswith(prefix))
        print(f"{name:20s}: {count:2d} vulnerabilities")
    
    print()
    
    # Show files with most vulnerabilities
    print("3. FILES WITH VULNERABILITIES")
    print("-" * 80)
    
    file_counts = {}
    for vid, files in code_markers.items():
        for file_path in files:
            if file_path not in file_counts:
                file_counts[file_path] = []
            file_counts[file_path].append(vid)
    
    sorted_files = sorted(file_counts.items(), key=lambda x: len(x[1]), reverse=True)
    for file_path, vids in sorted_files[:10]:
        print(f"{len(vids):2d} vulnerabilities: {file_path}")
    
    print()
    
    # Summary
    print("4. SUMMARY")
    print("-" * 80)
    
    if not missing_in_code and not missing_in_catalog:
        print("✓ All vulnerabilities properly documented")
        print("✓ Catalog and code are in sync")
        return 0
    else:
        print("⚠️  Documentation incomplete")
        if missing_in_code:
            print(f"   - {len(missing_in_code)} vulnerabilities missing code markers")
        if missing_in_catalog:
            print(f"   - {len(missing_in_catalog)} code markers missing catalog entries")
        return 1


if __name__ == "__main__":
    root = Path(__file__).parent.parent
    exit_code = verify_vulnerabilities(root)
    exit(exit_code)
