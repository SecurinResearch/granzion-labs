
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd()))

try:
    from src.scenarios.discovery import discover_scenarios
    print("Discovering scenarios...")
    scenarios = discover_scenarios()
    print(f"Discovered {len(scenarios)} scenarios.")
    for s in scenarios:
        print(f"Scenario {s.id}: has owasp_mappings={getattr(s, 'owasp_mappings', 'MISSING')}")
        print(f"Scenario {s.id}: has owasp_mapping={getattr(s, 'owasp_mapping', 'MISSING')}")
except Exception as e:
    import traceback
    traceback.print_exc()
