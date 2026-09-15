# Link connections

A read-only graph lookup graded entirely from Semble API state. No judge.

```sh
just evals run link-connections --model luna --repetitions 5
```

The user is about to read "AI as Normal Technology" and asks what people on Semble have connected it to and how each connected link relates, as recorded. The checker enumerates the URL's connections before and after the actor. A pass requires every connected link to appear and the passage after each link, up to the next connected link, to name the recorded relationship type (with stem tolerance: "led to" for LEADS_TO, "pushes back" for OPPOSES) and no other type. Drift makes the run inconclusive; execution limits are failures; a URL with no connections is inconclusive rather than graded.

When written the URL had four incoming connections of three types (RELATED, LEADS_TO, SUPPORTS), two with curator notes. Limitations: the API's per-url connection listing does not include the curator, so attribution is not graded; type detection is keyword-based and an answer that discusses a link's relationship in unusual words may fail the label check even when correct. Notes are not graded.
