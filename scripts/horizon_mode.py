"""switch the hosted semble mcp between code mode and jev mode.

    HORIZON_API_KEY=... uv run scripts/horizon_mode.py jev
    HORIZON_API_KEY=... uv run scripts/horizon_mode.py code
    HORIZON_API_KEY=... uv run scripts/horizon_mode.py status

a switch writes SEMBLE_MCP_MODE to the production environment variables and
builds main's head as a new version, deployed to production on success:
horizon only delivers changed variables through a new build, and refuses to
redeploy the version that is already live. TYPESAFE_API_KEY must already be a
production variable before the first switch to jev: the server refuses to
start in jev mode without it.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time

import httpx2 as httpx

API = "https://horizon.prefect.io/api/v0"
ORGANIZATION = "zzstoatzz"
PROJECT = "semble"
REPOSITORY = "zzstoatzz/semble"
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


def main_sha() -> str:
    out = subprocess.run(
        ["git", "ls-remote", f"https://github.com/{REPOSITORY}.git", "refs/heads/main"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return out.split()[0]


def set_variable(http: httpx.Client, base: str, key: str, value: str) -> None:
    url = f"{base}/environments/production/secrets"
    existing = {v["keyName"] for v in items(http.get(url))}
    if key in existing:
        response = http.patch(f"{url}/{key}", json={"value": value})
    else:
        response = http.post(
            url, json={"keyName": key, "value": value, "sensitive": False}
        )
    response.raise_for_status()


def build_and_deploy(http: httpx.Client, base: str, target_id: str, sha: str) -> None:
    """build main's head as a new version and deploy it to production.

    horizon refuses to redeploy a version that is already live (409), and a
    changed environment variable only reaches server code through a new
    build, so a mode switch is a rebuild of the same commit."""
    configuration = http.get(f"{base}/configuration").json()
    response = http.post(
        f"{base}/versions",
        json={
            "source": {
                "kind": "github",
                "repository": REPOSITORY,
                "revision": {"kind": "commit", "sha": sha},
            },
            "build": configuration["defaultBuild"],
            "deploy": {"targetIds": [target_id]},
        },
    )
    response.raise_for_status()
    version_id = response.json()["id"]
    print(f"building version {version_id} from {sha[:8]}")
    started = time.monotonic()
    while True:
        version = http.get(f"{base}/versions/{version_id}").json()
        if version["status"] == "failed":
            raise SystemExit(f"build failed: {version.get('error')}")
        deployments = [
            d
            for d in items(http.get(f"{base}/deployments"))
            if d["versionId"] == version_id
        ]
        if deployments and deployments[0]["status"] == "succeeded":
            return
        if deployments and deployments[0]["status"] == "failed":
            raise SystemExit(f"deployment failed: {deployments[0].get('error')}")
        if time.monotonic() - started > 900:
            raise SystemExit(f"version {version_id} not deployed after 15 minutes")
        time.sleep(10)


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
        set_variable(http, base, MODE_VARIABLE, mode)
        build_and_deploy(http, base, target_id, main_sha())
        tools = asyncio.run(served_tools(url))
        if not EXPECTED_TOOLS[mode] <= tools:
            raise SystemExit(
                f"deployed, but {url} serves {sorted(tools)}, not {mode} mode"
            )
        print(f"{url} is serving {mode} mode: {', '.join(sorted(tools))}")


if __name__ == "__main__":
    main()
