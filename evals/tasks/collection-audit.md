# Collection audit

A read-only maintenance task graded entirely from Semble API state. No judge.

```sh
just evals run collection-audit --model luna --repetitions 5
```

The user is helping `joe.germuska.com` tidy their library and asks which collections are empty or hold a single card, and which saved links are not in any collection. The checker lists the account's collections with card counts and its uncollected cards before and after the actor. A pass requires every collection with a card count of 0 or 1 to be named and every uncollected link to appear (trailing-slash tolerant, prefix-safe). Drift makes the run inconclusive; execution limits are failures.

When written the account had 14 collections (1 empty, 2 single-card), 195 cards, and 6 uncollected links, so both servers can answer in a handful of calls; the `uncollected` filter on the list endpoint makes a full scan unnecessary for a server that exposes it. Limitations: coverage only, so over-reporting is not penalized; the account is a real public user whose library changes, and expected values are recomputed live each run.
