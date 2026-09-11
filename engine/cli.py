"""Command-line interface for the Cyber Digital Twin and Attack Path Simulation."""

import sys
import argparse
from pathlib import Path

from engine.twin import FinBankTwin
from engine.rules import RuleEngine
from engine.attack_path import StatefulAttackEngine


def render_attack_path_demo(twin: FinBankTwin) -> str:
    """Demonstrate stateful attack path discovery and MFA What-If analysis."""
    engine = StatefulAttackEngine(twin)
    lines = []
    lines.append("")
    lines.append("========================================")
    lines.append("FINBANK ATTACK PATH ANALYSIS")
    lines.append("========================================")
    lines.append("")
    lines.append("Initial Foothold:")
    lines.append("corp-workstation")
    lines.append("")
    lines.append("Target:")
    lines.append("backup-vault")
    lines.append("")

    # 1. Baseline analysis: MFA Disabled in-memory
    mfa_control = twin.controls.get("ctrl-mfa")
    orig_enabled = mfa_control.enabled if mfa_control else True
    orig_status = mfa_control.status if mfa_control else "active"

    if mfa_control:
        mfa_control.enabled = False
        mfa_control.status = "disabled"

    res_off = engine.find_attack_paths(
        initial_node="corp-workstation",
        target_node="backup-vault",
        initial_capabilities=["admin_credentials"],
        initial_privileges=["infrastructure_admin"]
    )

    if res_off["target_reachable"] and res_off["paths"]:
        lines.append("Reachable:")
        lines.append("YES")
        lines.append("")
        lines.append("Attack Path:")
        # Format path using friendly names without 'asset-' prefix
        path_nodes = [
            n.replace("asset-", "").replace("id-", "")
            for n in res_off["paths"][0]["nodes"]
        ]
        lines.append("\n  ↓\n".join(path_nodes))
    else:
        lines.append("Reachable:")
        lines.append("NO")

    lines.append("")
    lines.append("----------------------------------------")
    lines.append("MFA ENABLED")
    lines.append("----------------------------------------")
    lines.append("")

    # 2. What-If analysis: MFA Enabled in-memory
    if mfa_control:
        mfa_control.enabled = True
        mfa_control.status = "active"

    res_on = engine.find_attack_paths(
        initial_node="corp-workstation",
        target_node="backup-vault",
        initial_capabilities=["admin_credentials"],
        initial_privileges=["infrastructure_admin"]
    )

    if res_on["target_reachable"]:
        lines.append("Reachable:")
        lines.append("YES")
    else:
        lines.append("Reachable:")
        lines.append("NO")
        lines.append("")
        if res_on["blocked_steps"]:
            first_blocked = res_on["blocked_steps"][0]
            from_node = first_blocked["from"].replace("asset-", "").replace("id-", "")
            to_node = first_blocked["to"].replace("asset-", "").replace("id-", "")
            lines.append("Blocked:")
            lines.append(f"{from_node} -> {to_node}")
            lines.append("")
            lines.append("Reason:")
            lines.append(first_blocked["reason"])

    lines.append("========================================")

    # Restore original control state in memory
    if mfa_control:
        mfa_control.enabled = orig_enabled
        mfa_control.status = orig_status

    return "\n".join(lines)


def main() -> int:
    # Ensure stdout handles UTF-8 correctly across Windows terminals
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="Cyber Digital Twin Engine - Graph Ingestion & Attack Path Analysis"
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
    parser.add_argument(
        "--no-attack",
        action="store_true",
        help="Skip stateful attack path analysis"
    )

    args = parser.parse_args()
    scenario_path = Path(args.scenario)

    if not scenario_path.exists():
        print(f"Error: Scenario file '{scenario_path}' does not exist.", file=sys.stderr)
        return 1

    twin = FinBankTwin.from_file(scenario_path)

    # 1. Print the Phase 1 pipeline flow banner
    print(twin.render_flow_banner(source_file=scenario_path.name))

    # 2. Detailed breakdown if requested
    if args.detail:
        print()
        twin.print_detailed_breakdown()

    # 3. Print Attack Path demonstration unless suppressed
    if not args.no_attack:
        print(render_attack_path_demo(twin))

    return 0


if __name__ == "__main__":
    sys.exit(main())
