# Semble app-password routing after a PDS migration

Verified 2026-09-12 against Semble source commit `463eda035983f7d80435f690953df95cc0695493` and live endpoints.

bufo.uk's DID document identifies `https://pds.zat.dev` as its PDS. The account is active there. The same app password also authenticates its old, deactivated account through `https://bsky.social`.

| Login endpoint | Result | Account active | Token audience / current service |
|---|---|---|---|
| bsky.social | 200 | false, deactivated | did:web:jellybaby.us-east.host.bsky.network |
| pds.zat.dev | 200 | true | DID document advertises pds.zat.dev |

Semble's `network.cosmik.server.createSession` accepted the SOPS-stored app password and returned success, but subsequent `card.addUrl` failed with `Account is deactivated`. This happens because `AppPasswordSessionService` creates and restores agents against a fixed `bsky.social` endpoint. `ATProtoAgentService` also constructs publishing/service-account agents against that endpoint. The ATProto SDK accepts an inactive login response; Semble previously did not check its `active` field. The SDK's persisted session data does not retain the PDS endpoint, so fixing initial login alone is insufficient.

ZDS is not the deactivated account. Reactivating the old Bluesky copy would be the wrong repair. Changing the MCP prompt or model budget cannot fix this failure either.

## Local repair

Worktree: `/Users/nate/.cache/worktrees/semble-pds-auth`, branch `codex/resolve-app-password-pds`.

Upstream: [cosmik-network/semble#930](https://github.com/cosmik-network/semble/pull/930) (draft). The PDS-aware agent constructor is `createPdsAgent` in `PdsAgent.ts`; constructing a protocol agent is separate from authentication, so keep general PDS behavior out of app-password-specific names. As of 2026-09-14 the PR had no reviews; its only failing check was Vercel's fork-preview authorization gate, which a Cosmik maintainer must approve and which is not a test or build failure.

- Resolve the handle/DID to its current DID-document PDS before app-password login and session restoration.
- Construct subsequent publisher/service-account agents at that PDS too.
- Reject inactive sessions and sessions belonging to another DID.
- If stored tokens from a previous PDS are rejected, log in at the current PDS and persist the replacement session.
- Fail resolution rather than falling back to a fixed Bluesky host.

No ZDS code or deployment changes were necessary. The patch is local; applying it to Semble's hosted backend requires upstream deployment. Semble is MIT-licensed open source, but its hosted backend is not our MCP deployment.

## Validation

Nine targeted tests passed across the session-service regressions and existing OAuth-agent tests. The regressions exercise the real AtpAgent against supplied HTTP responses, including stale-token recovery and inactive-account rejection.

Live validation used the same SOPS credential without logging its value: login, persisted-session restoration, publisher restoration, and a temporary `network.cosmik.collection` write all succeeded at `pds.zat.dev`. The temporary collection was deleted, and a subsequent read returned RecordNotFound. Evidence: `evals/results/semble-pds-auth-diagnosis/live-smoke.json`.

The full repository typecheck has three errors in OAuthClientFactory and MetadataWorkerProcess. Running the unchanged baseline with the same dependencies reproduced all three. The initial clean install also encountered an out-of-sync upstream lockfile; dependencies were installed without changing the lockfile. These checks are reported separately from the passing focused tests and live smoke.

No model evaluations completed during the failed hosted-backend preflights, so they provide no evidence about either MCP's task performance.
