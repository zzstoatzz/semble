# Link context

A read-only lookup graded entirely from Semble API state. No judge.

```sh
just evals run link-context --model luna --repetitions 5
```

The user was sent `https://habitat.network/` and asks who on Semble saved it, which collections it is filed in, and what people wrote about it in notes, with handles, collection names, and note authors. The checker enumerates the URL's libraries, collections, and note cards before and after the actor. A pass requires every saver handle, every collection name, and every note author to appear in the answer (case-insensitive substring). Any drift between the two observations makes the run inconclusive; execution limits are failures.

This task is deliberately small: three endpoint calls and a few dozen rows. It exists so the suite has a case where holding raw tool output in context is no disadvantage and a plain tool-per-endpoint server should be at least even. Limitations: the grade is coverage only, so an answer that lists extra people or collections is not penalized; attribution of notes to authors is checked by presence, not adjacency.
