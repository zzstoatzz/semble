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
