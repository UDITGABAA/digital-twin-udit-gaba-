"""Command-line interface for the Cyber Digital Twin."""

import sys
import argparse
from pathlib import Path
from engine.twin import FinBankTwin


def main() -> int:
    # Ensure stdout handles UTF-8 correctly across Windows terminals
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Cyber Digital Twin Engine - Graph Ingestion & Detection"
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default="scenarios/scenario.json",
        help="Path to scenario JSON file (default: scenarios/scenario.json)"
    )
    parser.add_argument(
        "-d", "--detail",
        action="store_true",
        help="Display detailed tabular breakdown of detected entities"
    )

    args = parser.parse_args()
    scenario_path = Path(args.scenario)

    if not scenario_path.exists():
        print(f"Error: Scenario file '{scenario_path}' does not exist.", file=sys.stderr)
        return 1

    twin = FinBankTwin.from_file(scenario_path)
    
    # Print the requested pipeline flow banner
    print(twin.render_flow_banner(source_file=scenario_path.name))
    
    if args.detail:
        print()
        twin.print_detailed_breakdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())
