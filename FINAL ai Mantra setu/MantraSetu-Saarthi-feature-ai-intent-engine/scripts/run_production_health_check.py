"""Automated Production Health Check CLI Script for MantraSetu AgentOS."""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.deployment.deployment_manager import ProductionDeploymentManager


def main():
    print("[MantraSetu AgentOS] Executing Automated Production Health Probe...")
    mgr = ProductionDeploymentManager()
    status = mgr.get_deployment_status()

    print(f"-> Environment: {status.environment}")
    print(f"-> System Version: {status.version}")
    print(f"-> Readiness Score: {status.readiness_score} / 100.0")
    print("-> Subsystem Readiness Checks:")

    all_passed = True
    for svc, healthy in status.services_healthy.items():
        state_str = "PASS" if healthy else "FAIL"
        print(f"   - {svc:30s}: [{state_str}]")
        if not healthy:
            all_passed = False

    if all_passed and status.readiness_score >= 95.0:
        print("\n[SUCCESS] All production health probes PASSED. AgentOS is READY for traffic.")
        sys.exit(0)
    else:
        print("\n[ERROR] Production health probe FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
