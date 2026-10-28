# Example workflows

Specs for the workflow authoring tool (`docs/WORKFLOW_AUTHORING.md`). Each is
a small real use case. The test suite builds and inspects every one
(`tests/test_authoring_examples.py`), so a change to a node's contract that
breaks an example fails the suite instead of leaving the example stale.

Build one into your library, then open it from the Workflow Library or run it:

```bash
aotn build examples/pause_and_wait.json
aotn inspect "Example - Pause and wait"
aotn run "Example - Pause and wait"
```

| Spec | Shows | Needs before running |
|---|---|---|
| `ask_hosted_question.json` | One Question → hosted Answer as JSON → Check reply → Text Output | Add `ANTHROPIC_API_KEY` in Secrets; consumes API credits; no live call was made for this example |
| `context_pack.json` | Disk/Git Vault facts plus log excerpts → Context Pack → investigation evidence | Configure the service folder/log, allowed folders and the investigation profile/bridge; request queueing is not finding completion |
| `pause_and_wait.json` | Parallel Branch, Sleep, Wait Until waiting for another path | nothing |
| `ask_and_branch.json` | User Text Input, Conditional choosing one path | answering the prompt |
| `vault_handoff.json` | Vault output on Start, Set/Get Variable, a Text Output reading the Vault | nothing |
| `fetch_and_save.json` | HTTP Request (text) into File Write, then File Manager showing the file | network; writes `/tmp/aotn_examples/example.html` |
| `catch_http_errors.json` | An inline Error Mux routing `network`/`timeout` to an "Offline" path, other errors to "unmatched" | nothing (the URL is meant to fail) |
| `summarise_file.json` | File Reader into Chat Completion's document, Vault output of the summary | `/tmp/aotn_examples/notes.txt` and a secret named `anthropic_api_key` |

Names start with "Example - " so they sort together and never clash with your
own workflows; `aotn build` refuses a name that is already saved.
