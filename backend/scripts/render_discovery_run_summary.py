from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any


def render_summary(payload: dict[str, Any]) -> str:
    agents = list(payload.get("agents") or [])
    counts = Counter(str(agent.get("status") or "unknown") for agent in agents)
    documents = list((payload.get("manifest") or {}).get("documents") or [])
    diff = payload.get("diff") or {}
    run = payload.get("run") or {}
    lines = [
        "## AMC discovery supervisor",
        "",
        f"- Run: `{run.get('run_id') or 'unknown'}`",
        f"- Status: **{payload.get('status') or 'unknown'}**",
        f"- Expected month: `{run.get('expected_month') or 'not set'}`",
        f"- Completed agents: **{counts.get('completed', 0)}/{len(agents)}**",
        f"- Discovered documents: **{len(documents)}**",
        f"- Promotable documents: **{sum(document.get('discovery_agent_status') == 'promotable' for document in documents)}**",
        f"- Meaningful changes: **{sum(len(diff.get(kind) or []) for kind in ('added', 'removed', 'changed'))}**",
        "",
        "| AMC | Status | Documents |",
        "| --- | --- | ---: |",
    ]
    for agent in agents:
        lines.append(
            f"| {agent.get('amc') or 'unknown'} | {agent.get('status') or 'unknown'} | "
            f"{len(agent.get('documents') or [])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a GitHub-friendly AMC discovery run summary.")
    parser.add_argument("report_path")
    args = parser.parse_args()

    payload = json.loads(Path(args.report_path).read_text(encoding="utf-8"))
    rendered = render_summary(payload)
    print(rendered, end="")

    step_summary_path = os.getenv("GITHUB_STEP_SUMMARY", "").strip()
    if step_summary_path:
        with Path(step_summary_path).open("a", encoding="utf-8") as handle:
            handle.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
