# Shared saves

A read-only aggregation task graded entirely from Semble API state. No answer judge or pairwise judge runs.

```sh
just evals run shared-saves --model luna --repetitions 3
```

The user names six people they follow (hyl.st, zafarali.me, aaronstevenwhite.io, finest.day, tgoerke.bsky.social, blue-phia.bsky.social) and asks which links more than one of them has saved, and who saved each. Answering correctly requires paginating six public libraries (about 1,200 cards over roughly fifteen pages when written), grouping by URL, and reporting every URL with two or more savers together with the exact saver set.

The checker enumerates the same six libraries before and after the actor with explicit pagination invariants, computes the shared set with trailing-slash equivalence, and grades the final answer deterministically:

- every shared URL must appear;
- no URL saved by only one of the six may appear;
- the passage following each shared URL, up to the next shared URL, must name exactly that URL's savers among the six handles.

A URL that is a prefix of a longer URL does not count as the shorter one. If the shared set differs between the before and after observations the run is inconclusive. Execution limits are failures.

Limitations: attribution is checked by handle mentions near each URL, so an answer that groups links under saver headings instead of listing savers per link will fail even if it is correct; the prompt asks for savers per link. The six accounts are real public users whose libraries change over time; expected results are recomputed live each run, so difficulty drifts with their activity. The task does not check counts, ordering, or prose.

## First run, 2026-09-14

Three Luna repetitions per server, results in `results/2026-09-14T17-30-53.178Z-73382`:

| MCP | Pass | Median seconds | Input tokens per cell | Actor cost per cell |
|---|---:|---:|---:|---:|
| code-mode | 3 of 3 | 61 | 17k to 30k | about $0.005 |
| official | 0 of 3 | 26 | 437k to 1.34M | $0.17 to $0.38 |

Every code-mode run paginated all six libraries inside execute and returned the 19 shared links with correct savers. One execute hit the 30-second sandbox cap at 31 seconds and the model recovered by splitting the work; the cap was raised to 60 seconds afterwards. Official runs either stopped after the first page of each library and said so, or fetched every page and overflowed the model's context window with 2.6 MB of card JSON before answering. Token and cost figures are Pi's SDK estimates.
