#!/usr/bin/env python3
"""
Run all 15 attack scenarios and generate a comprehensive report.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.scenarios.discovery import discover_scenarios
from src.scenarios.engine import ScenarioEngine
from datetime import datetime
import json

def run_all_scenarios():
    """Execute all scenarios and generate report."""
    
    print("\n" + "="*80)
    print("GRANZION LAB - RUNNING ALL SCENARIOS")
    print("="*80 + "\n")
    
    start_time = datetime.now()
    
    # Discover scenarios
    print("1. Discovering scenarios...")
    scenarios = discover_scenarios()
    print(f"   ✓ Found {len(scenarios)} scenarios\n")
    
    if not scenarios:
        print("   ✗ No scenarios found!")
        return False
    
    # Sort scenarios by ID
    scenarios = sorted(scenarios, key=lambda s: s.id)
    
    # Initialize engine
    print("2. Initializing scenario engine...")
    engine = ScenarioEngine()
    print("   ✓ Engine ready\n")
    
    # Execute all scenarios
    print("3. Executing all scenarios...")
    print("   (This may take several minutes)\n")
    
    results = []
    successful = 0
    failed = 0
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"   [{i}/{len(scenarios)}] Running {scenario.id}: {scenario.name}...")
        
        try:
            result = engine.execute_scenario(scenario)
            results.append({
                'scenario': scenario,
                'result': result,
                'success': result.success
            })
            
            if result.success:
                successful += 1
                print(f"        ✓ Success ({result.duration_seconds:.2f}s)")
            else:
                failed += 1
                print(f"        ✗ Failed ({result.duration_seconds:.2f}s)")
                
        except Exception as e:
            failed += 1
            print(f"        ✗ Error: {str(e)[:100]}")
            results.append({
                'scenario': scenario,
                'result': None,
                'success': False,
                'error': str(e)
            })
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Generate report
    print("\n" + "="*80)
    print("EXECUTION SUMMARY")
    print("="*80 + "\n")
    
    print(f"Total Scenarios: {len(scenarios)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(successful/len(scenarios)*100):.1f}%")
    print(f"Total Duration: {duration:.2f}s")
    print(f"Average Duration: {(duration/len(scenarios)):.2f}s per scenario\n")
    
    # Detailed results
    print("="*80)
    print("DETAILED RESULTS")
    print("="*80 + "\n")
    
    for item in results:
        scenario = item['scenario']
        result = item.get('result')
        success = item['success']
        
        status_icon = "✓" if success else "✗"
        print(f"{status_icon} {scenario.id}: {scenario.name}")
        print(f"   Category: {scenario.category.value}")
        print(f"   Difficulty: {scenario.difficulty.value}")
        print(f"   Threats: {', '.join(scenario.threat_ids)}")
        
        if result:
            print(f"   Steps: {result.steps_executed} ({result.steps_succeeded} succeeded, {result.steps_failed} failed)")
            print(f"   Duration: {result.duration_seconds:.2f}s")
            
            if result.evidence:
                print(f"   Evidence:")
                for evidence in result.evidence[:3]:  # Show first 3
                    text = evidence if isinstance(evidence, str) else str(evidence)
                    print(f"     - {text[:80]}{'...' if len(text) > 80 else ''}")
                if len(result.evidence) > 3:
                    print(f"     ... and {len(result.evidence) - 3} more")
        elif 'error' in item:
            print(f"   Error: {item['error'][:100]}")
        
        print()
    
    # Threat coverage
    print("="*80)
    print("THREAT COVERAGE")
    print("="*80 + "\n")
    
    all_threats = set()
    for item in results:
        if item['success']:
            all_threats.update(item['scenario'].threat_ids)
    
    print(f"Threats Validated: {len(all_threats)}")
    print(f"Threats: {', '.join(sorted(all_threats))}\n")
    
    # Category breakdown
    print("="*80)
    print("CATEGORY BREAKDOWN")
    print("="*80 + "\n")
    
    categories = {}
    for item in results:
        cat = item['scenario'].category.value
        if cat not in categories:
            categories[cat] = {'total': 0, 'success': 0}
        categories[cat]['total'] += 1
        if item['success']:
            categories[cat]['success'] += 1
    
    for cat, stats in sorted(categories.items()):
        success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"{cat.capitalize():20s}: {stats['success']}/{stats['total']} ({success_rate:.0f}%)")
    
    print("\n" + "="*80)

    # Clean up scenario-created agents so only canonical four remain
    try:
        from scripts.cleanup_scenario_agents import cleanup_scenario_agents
        removed = cleanup_scenario_agents()
        if removed:
            print(f"\n   Cleaned up {removed} scenario-created agent(s) (canonical agents only in DB).\n")
    except Exception as e:
        print(f"\n   (Cleanup skipped: {e})\n")
    
    if successful == len(scenarios):
        print("\n✓✓✓ ALL SCENARIOS EXECUTED SUCCESSFULLY ✓✓✓")
        print("\nThis confirms:")
        print("  ✓ All agents are working")
        print("  ✓ All MCPs are working")
        print("  ✓ All database operations are working")
        print("  ✓ All identity operations are working")
        print("  ✓ All threat categories are covered")
        print("  ✓ System is ready for red teaming\n")
        return True
    else:
        print(f"\n⚠ {failed} SCENARIO(S) FAILED")
        print("\nSome scenarios encountered issues.")
        print("Check the detailed results above for more information.\n")
        return False


def main():
    """Run all scenarios."""
    success = run_all_scenarios()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
