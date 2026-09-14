# reading recommendation

Run `just evals run reading-recommendation --model luna --repetitions 1` for a
single comparison. The input handle is in `library.json`.

The user asks for a half-hour reading list for the named person: three unsaved
things ordered by value to that person, with a reason the first deserves priority. No preferred
interest, URL, or search strategy is supplied. Older material can be appropriate;
the question is current usefulness, not a fixed publication cutoff.

The complete library and collection observations establish the user's actual
saved interests and novel-versus-saved status. Candidate metadata and bounded public HTTPS page text are fetched after
the answer. The judge requires a useful, grounded comparison among the selected
items, not merely three links with generic descriptions. Passing answers may
then be compared blind in both presentation orders.

See [the suite contract](../../docs/portable-eval-suite.md) for scoring, evidence
coverage, cost controls and limitations.
