# HTTP, Notify me and If changed metadata — 2026-11-01

Base: main `23a518e`; branch `codex/review-network-notify-change` in
`/home/makin/src/review-network-notify-change`. Foundational scope: reviewed records
and executable claims. Initial head `f436524` changed metadata only; the reviewer
follow-up below also restricts HTTP Request URLs and adds its scheme error.
Defaults, ports and draft admission are unchanged.

## Source review

| Record | Source-backed effects, needs and execution |
|---|---|
| HTTP Request | Synchronous urllib request to the configured URL, including internet URLs. POST sends configured text or input as text/bytes/JSON; GET has no body. Optional bearer token; remote endpoint may change state or charge. File mode needs run session/storage and streams raw bytes to a file reference with lifetime. Success cleanup deletes run files unless kept; failures retain them. Text decoding, timeout/network/status errors and bounded error-body details are covered. |
| Notify me | Local outbox/receipt/repeat-file writes, followed by delegated Telegram messaging. No Telegram request is made by the node. Hermes uses a separately installed 5-minute drain cycle; queued is not delivered and the node does not install/check the job. The original wire is forwarded by default, even with a Vault message source; receipt output is optional. Blank/repeated messages, escaping, truncation, destinations and queue errors keep existing rules. |
| If changed | Locked persistent compare-and-save, including first use and unchanged values. Scope is workflow name or all workflows on the machine. Exact sorted-key JSON or whitespace/case-insensitive comparison; routes current value only. Suppression preserves save/route. Missing inputs, store failures, oversized values and Carry on follow existing code. File references are compared as records, not by reading files. |

HTTP cost is variable because the endpoint can charge; its synchronous network
wait depends on timeout/response size. Notify has no built-in usage fee; queue
lock/I/O and later delivery make timing variable. If changed has no usage fee;
local lock/I/O determines its wait. Delivery prerequisites for Notify are stated
separately from the local prerequisites for queuing. Records do not grant approval.

The review manifest binds each record to its node, helpers, supporting claims and
content digest. Notify also binds the checked delivery documentation and drain
entry script. Author and verifier labels identify local authoring and a separate
source/claims recheck pass; they do not claim a second human's review. The PR is
submitted for independent review before merge, as the metadata process requires.

## Executable evidence

`tests/test_network_notify_change_metadata.py` adds 35 cases with external
network/process escape blocked. HTTP transport responses/errors are faked;
notification queuing and saved-value comparisons use real helpers in per-test
temporary storage. No paid calls, real Telegram sends or owner files are used.

Claims cover POST bodies and bearer header, configured bodies versus GET, charset
and replacement decoding, response-file bytes/lifetime, declared transport errors,
pre-transport validation, notification receipt versus original-wire/silent outputs,
queue failure policy, saved comparison across distinct run IDs, first-use policy,
payload suppression and store errors. Existing notification/store/drain tests
supply additional escaping, repeat, destination, empty-message, corruption and
hand-off evidence. The 5-minute cadence is the documented deployment contract,
not a scheduler installed or exercised by these tests.

The three types leave `PENDING_REVIEW`, producing **21 reviewed / 22 pending /
16 dev-only** of 59 registered types. Exact inventory assertions were updated to
these expected counts; record validation and fingerprint assertions stay strict.
New content digests and LF-normalized source hashes are in
`backend/node_metadata_review.json`.

The documented receipt exporters were run deliberately:

- `AOTN_CLAIMS_REPORT=/tmp/network-metadata-claims.json python -m pytest tests/test_node_claims.py::test_claims_receipt`.
- `AOTN_FLOW_CLAIMS_REPORT=/tmp/network-metadata-flow-claims.json python -m pytest tests/test_flow_claims.py::test_flow_claims_receipt`.

Reviewed diffs: generic claims change only source hashes, the three reviewed
booleans and an explicit isolated-file boundary label for If changed; existing runtime observations/claim outcomes do not change. The flow
receipt changes only source hashes; its flow records, provenance and 104 scenario
observations are unchanged. The baseline snapshot and current claims table mark
the three types reviewed without changing their supported standard flags.

## Draft boundaries

No change to `ADMITTED`, roles, draft prompts, trial fixtures or sets. New tests
assert that none of the three types is admitted or present in role candidates;
existing frozen-designer and admission checks remain in the full suite. The new
records are available to catalogue/inspection clients without authorizing drafts.

## Initial metadata-head verification

Focused source/metadata/node/store checks plus receipt exporters: **330 passed**.
A final source recheck clarified that Carry on can suppress a blank-name save
failure but never a missing input; four additional cases cover that distinction.
Final dedicated claims plus both receipt exporters: **37 passed**.
Full suite from the app directory, using the shared interpreter and exact command
`python -m pytest -q -n auto`: **5,353 passed, 187 skipped**, 54.79 seconds.
`git diff --check` and changed-document local Markdown links pass. Palette, roles,
prompt/schema files, trial files and runtime node files were compared to main
`23a518e` and are unchanged.

The initial full run found the missing explicit If changed boundary declaration
(5,348 passed / 187 skipped / one failure); it was added without relaxing the
registry gate. That full suite then passed 5,349 tests / 187 skipped before the
four final cases were added.

## Reviewer follow-up: restrict HTTP Request schemes

Merged main `a21f8cd` into this branch before editing. The reviewer correctly
identified that unrestricted urllib could read `file:` and `data:` URLs despite
the record requiring networking. The runtime now accepts only `http` and `https`.
A missing URL retains `missing_url`; any other scheme or missing scheme fails
`unsupported_url_scheme` with: **Only http:// and https:// URLs are supported.**
The node validates before building a request/opener, reading Secrets or requiring
a response-file run session. Rejected URLs cannot read a local file.

A private opener installs an HTTP-only redirect handler without replacing urllib's
global opener. It checks every redirect hop before following it, including the
301/302/303/307/308 aliases and subsequent hops. Rejected redirects close the
response without dispatching another request. HTTP, HTTPS, relative paths and
scheme-relative redirects retain urllib's ordinary behavior. This also replaces
urllib's default FTP-redirect allowance with the same plain coded rejection.

The helper spec and generated error-declaration assertion include the new
non-retryable error. Metadata now explicitly limits URLs/redirects to HTTP(S),
requires networking for actual requests, limits local-file needs to file response
mode, and keeps POST data transmission explicit. Existing HTTP test doubles moved
from global `urlopen` to this node's private `_open_http` boundary; their URLs,
response expectations, routing and cleanup assertions were preserved.

### Scheme dependency search

Before adding the negative fixtures, tracked JSON/YAML node configs and the
Python tests/specs/workflows were searched for unsupported schemes. No existing
HTTP Request dependency on a non-HTTP(S) URL was found. The three explicit tracked
HTTP Request workflow URLs are:

- `examples/catch_http_errors.json`: `https://unreachable.invalid/data`.
- `examples/fetch_and_save.json`: `https://example.com`.
- `integrations/hermes/h2-http-watchdog.json`: `http://127.0.0.1:8765/health`.

Other-scheme occurrences are unrelated and unchanged: `tests/test_stash.py` and
`backend/paste_parser.py` support file-URI pastes; the Stash proposal documents
that format. `tests/test_local_model.py` uses an FTP URL as an invalid service-base
case. There were no existing `data:text` HTTP fixtures. New file/data/FTP cases
are explicit refusal regressions, not migrated workflows.

### Verification and pins

`tests/test_http_request_schemes.py` exercises the real urllib opener/redirect
dispatch with fake HTTP/HTTPS handlers and forbidden file/data/FTP/socket handlers.
No live HTTP request or local URL read occurs. Initial bad schemes (text/file
response modes), all five redirect statuses, valid redirect forms and a later
bad redirect after a valid hop are covered. Before the fix: **33 failed, 20 passed**;
with the later-hop case added: **54 pass**. Existing HTTP/routing/lifecycle/child
workflow focused checks also pass.

Record/source digests, the HTTP source-menu execute pin and the generic source
baseline were refreshed after rechecking the code. Generic/flow receipts were
re-exported deliberately; only source hashes changed from their post-main-merge
versions, with every observation and claim outcome unchanged. Other record
attestations affected by shared test-file changes were rechecked. The final
focused evidence run passed **261 tests**. Full-suite result pending.
