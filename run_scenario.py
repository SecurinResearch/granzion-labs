#!/usr/bin/env python3
"""
Run a specific attack scenario.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.scenarios.engine import ScenarioEngine
from src.scenarios.discovery import discover_scenarios, get_scenario_by_id

def main():
    parser = argparse.ArgumentParser(description="Run a specific Granzion Lab scenario")
    parser.add_argument("scenario_id", help="Scenario ID (e.g. s01, s02, s01_identity_confusion)")
    args = parser.parse_args()
    
    scenario_id = args.scenario_id.lower()
    
    print(f"Initializing Scenario Engine for '{scenario_id}'...")
    engine = ScenarioEngine()
    
    # Try to execute
    try:
        # Check if scenario exists first for better error message
        scenarios = discover_scenarios()
        target = next((s for s in scenarios if s.id.lower() == scenario_id or s.id.lower() == scenario_id.replace("_", "-")), None)
        
        if not target:
            # Try fuzzy match
            target = next((s for s in scenarios if scenario_id in s.id.lower()), None)
        
        if not target:
            print(f"Error: Scenario '{scenario_id}' not found.")
            print("Available scenarios:")
            for s in sorted(scenarios, key=lambda x: x.id):
                print(f"  - {s.id}: {s.name}")
            return 1
            
        print(f"Found scenario: {target.id}: {target.name}")
        print("Executing...")
        
        result = engine.execute_scenario(target)
        
        if result.success:
            print("\n✅ SCENARIO PASSED")
            return 0
        else:
            print("\n❌ SCENARIO FAILED")
            if result.errors:
                print(f"Errors: {result.errors}")
            return 1
            
    except Exception as e:
        import traceback
        print(f"\n❌ Execution Error: {e}")
        print(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit(main())
