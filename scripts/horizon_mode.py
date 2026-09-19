"""switch the hosted semble mcp between code mode and jev mode.

    HORIZON_API_KEY=... uv run scripts/horizon_mode.py jev
    HORIZON_API_KEY=... uv run scripts/horizon_mode.py code
    HORIZON_API_KEY=... uv run scripts/horizon_mode.py status

horizon passes a deployment's `env` map to the running server on top of the
project's environment variables, so a mode switch is a new deployment of the
artifact that is already live, with SEMBLE_MCP_MODE overridden. no rebuild.
the same value is written to the production environment variable so the next
build from main inspects and runs in the same mode. TYPESAFE_API_KEY must
already be a production variable before the first switch to jev: the server
refuses to start in jev mode without it.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

import httpx2 as httpx

API = "https://horizon.prefect.io/api/v0"
ORGANIZATION = "zzstoatzz"
PROJECT = "semble"
MODE_VARIABLE = "SEMBLE_MCP_MODE"
EXPECTED_TOOLS = {
    "code": {"search", "get_schema", "execute"},
    "jev": {"search_tools", "call_tool"},
}


def client() -> httpx.Client:
    key = os.environ.get("HORIZON_API_KEY")
    if not key:
        raise SystemExit("HORIZON_API_KEY is not set")
    return httpx.Client(
        base_url=API, headers={"Authorization": f"Bearer {key}"}, timeout=30
    )


def items(response: httpx.Response) -> list[dict]:
    response.raise_for_status()
    body = response.json()
    return body["items"] if isinstance(body, dict) else body


def locate(http: httpx.Client) -> tuple[str, str, str]:
    org = next(
        o for o in items(http.get("/me/organizations")) if o["slug"] == ORGANIZATION
    )
    project = next(
        p
        for p in items(http.get(f"/organizations/{org['id']}/projects"))
        if p["name"] == PROJECT
    )
    base = f"/organizations/{org['id']}/projects/{project['id']}"
    target = next(
        t for t in items(http.get(f"{base}/targets")) if t["slug"] == "production"
    )
    return base, target["id"], target.get("servingUrl") or target.get("url") or ""


def live_version(http: httpx.Client, base: str, target_id: str) -> str:
    deployments = [
        d
        for d in items(http.get(f"{base}/deployments"))
        if d["targetId"] == target_id and d["status"] == "succeeded"
    ]
    if not deployments:
        raise SystemExit("no successful production deployment to redeploy")
    deployments.sort(key=lambda d: d["finishedAt"] or "", reverse=True)
    return deployments[0]["versionId"]


def set_variable(http: httpx.Client, base: str, key: str, value: str) -> None:
    url = f"{base}/environments/production/secrets"
    existing = {v["keyName"] for v in items(http.get(url))}
    payload = {"keyName": key, "value": value, "sensitive": False}
    if key in existing:
        response = http.put(f"{url}/{key}", json={"value": value})
        if response.status_code == 405:
            response = http.patch(f"{url}/{key}", json={"value": value})
    else:
        response = http.post(url, json=payload)
    response.raise_for_status()


def deploy(
    http: httpx.Client, base: str, target_id: str, version_id: str, mode: str
) -> None:
    response = http.post(
        f"{base}/deployments",
        json={
            "targetId": target_id,
            "versionId": version_id,
            "env": {MODE_VARIABLE: mode},
        },
    )
    response.raise_for_status()
    deployment_id = response.json()["id"]
    started = time.monotonic()
    while True:
        state = http.get(f"{base}/deployments/{deployment_id}").json()
        if state["status"] == "succeeded":
            return
        if state["status"] in {"failed", "superseded"}:
            raise SystemExit(
                f"deployment {deployment_id} {state['status']}: {state.get('error')}"
            )
        if time.monotonic() - started > 600:
            raise SystemExit(
                f"deployment {deployment_id} still {state['status']} after 10 minutes"
            )
        time.sleep(5)


async def served_tools(url: str) -> set[str]:
    from fastmcp import Client

    async with Client(url) as session:
        return {tool.name for tool in await session.list_tools()}


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if mode not in {*EXPECTED_TOOLS, "status"}:
        raise SystemExit(__doc__)
    with client() as http:
        base, target_id, url = locate(http)
        if mode == "status":
            tools = asyncio.run(served_tools(url))
            current = next(
                (m for m, t in EXPECTED_TOOLS.items() if t <= tools), "unknown"
            )
            print(f"{url}: {current} ({', '.join(sorted(tools))})")
            return
        version_id = live_version(http, base, target_id)
        set_variable(http, base, MODE_VARIABLE, mode)
        print(f"redeploying version {version_id} with {MODE_VARIABLE}={mode}")
        deploy(http, base, target_id, version_id, mode)
        tools = asyncio.run(served_tools(url))
        if not EXPECTED_TOOLS[mode] <= tools:
            raise SystemExit(
                f"deployed, but {url} serves {sorted(tools)}, not {mode} mode"
            )
        print(f"{url} is serving {mode} mode: {', '.join(sorted(tools))}")


if __name__ == "__main__":
    main()
