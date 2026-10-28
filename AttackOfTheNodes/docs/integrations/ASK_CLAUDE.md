# Ask Claude

Complex → AI, direct add `ask_claude_node`. One Question plus optional Context
produces one text Answer. No tools, history or saved conversation. The official
`anthropic` Python SDK streams `POST /v1/messages` and assembles its final
message before publishing anything. No live API call was made during this build.

In **Options → 1 General**, choose **Claude model**:
`claude-haiku-5-5` (default), `claude-sonnet-5-5`, or `claude-opus-5-5`.
**Model override** offers those choices and **Options default**. Changing this
setting is sufficient; no prompt or provider-code edit is required.

Add **ANTHROPIC_API_KEY** in **Options → Secrets**. An environment key is never
used as a substitute. The endpoint is fixed to `https://api.anthropic.com`;
redirects, proxy discovery and trace export are disabled. No key setting exists
in workflow JSON. The SDK keeps its normal two retries, inside the node's
**Stop after (seconds)** deadline (default 120; range 10–600).

**Question** and **Context** each accept Upstream payload / Vault / Configured
text, with compatible typed Vault keys. Context also has **Not used**, its
default. Configured long text uses the shared preview/editor. Context is
separated from the question as data. **Claude context limit (characters)** is
independent of the local-model cap: default 100,000, range 1,000–200,000.
A blank per-node **Context limit** inherits it. Assembled Question + Context
must fit the effective limit + 12,000. Oversize errors before any API request;
there is no silent shortening. Context Pack retains its 4,000-per-item limit.

**Cache context** in Options is **off** (default), **5 min**, or **1 h**,
stored as `claude_cache_context` through ConfigurationManager. Off preserves
the original string request, question followed by Context, without a cache
marker. When enabled with nonblank Context, the user message contains two text
blocks: stable Context first with `cache_control: {"type": "ephemeral",
"ttl": "5m"}` (or `"1h"`), then the question without a marker. Empty, whitespace
or unused Context sends no marker. Changing only the question leaves the cached
prefix unchanged. The provider's minimum cacheable length and prefix-matching
rules still apply; selecting a TTL does not guarantee a cache hit.
The minimum cacheable prefix is 512 tokens for all three supported models.
Context below about 512 tokens (roughly 2,000 English-text characters) generally
won't cache. The threshold applies to the entire prefix through the marker,
including the system instruction and Context label, not Context alone; character
counts are only an approximation. Below the token threshold the request succeeds
without caching or an error, and both `cache_read_input_tokens` and
`cache_creation_input_tokens` stay at 0. The question after the marker does not
help reach the threshold.

**Effort** is low / medium / high, default low, sent as `output_config.effort`.
No temperature, top_p, top_k, thinking-disable or budget_tokens field is sent.
**Max output tokens** defaults to 2,048 (1–8,192). Thinking can consume output
budget; its blocks never become Answer. Answer is capped at 16,000 characters.
**Reply as JSON** adds a JSON-only instruction and checks strict JSON syntax
(no fences, repeated keys or non-finite numbers). It does not impose a schema:
use **Check reply** for expected fields/types. A JSON instruction is not a
provider guarantee, so a non-JSON response becomes `invalid_response`.

**Answer [string]** uses standard downstream/Vault routing and the standard
**Forward incoming payload unchanged** checkbox. Optional **Run details [var]**
is Vault only: model that served the reply, input/output tokens, cache read/write tokens (including writes by TTL), stop reason,
wall seconds and a USD **Estimate**. It contains no question, Context, thinking,
SDK exception body or API key. Answer masks only exact known Secrets values;
ordinary labels such as `key`,
`token` and `password_hint` remain data. JSON mode parses first, masks decoded
strings (including object keys), then serializes valid JSON text. SDK diagnostics
and Run details retain the shared credential redactor (labels plus known Secrets).
Successful calls also emit the existing `AGENT_USAGE_UPDATE` event, with a
unique invocation ID and sanitized usage, regardless of whether Run details is
saved to the Vault. Run history and CLI JSON expose these receipts in
`agent_usage`; `agent_usage_summary` totals their estimates. No question,
Context or Answer is included in the receipt. Failed calls retain the existing
error path and do not publish a successful usage receipt.
The supervisor's redaction and per-input error-record cap protect persisted failed inputs too.

Stop reason is checked before reading content. `refusal` errors with a category
(or `unspecified`); `max_tokens` errors as a cut-off reply. Other unfinished
stops also error. No Answer or Run details is published on failure. Auth/key,
rate-limit (numeric retry-after seconds), overload (529), connection, deadline,
provider and invalid-response errors have stable codes; raw provider messages
are not copied to durable errors. Node errors remain non-retryable by the
workflow; the SDK's transport retries are separate.

For Sonnet/Opus only, the SDK beta Messages stream sends
`betas=["server-side-fallback-2026-07-01"]`, `fallbacks="default"`.
Haiku sends neither. The provider may serve a fallback model. For streaming,
the serving model comes from the final usage iteration when present. Cost
estimation sums available per-attempt usage; unknown model prices yield an
unavailable estimate, never a borrowed rate. Displayed input/output counts are
the API's top-level counts for the serving attempt, not a sum across models.

Base prices per million tokens: Haiku $0.10 input / $0.50 output; Sonnet $2 /
$10; Opus $4 / $20. These are the owner-approved small estimate table, not a
billing quote. Haiku's documented >100,000-input-token tier is higher
($0.50 / $2.50). Cache reads cost 0.1× the base input rate for Haiku
($0.01/MTok at the base tier), and 0.05× for Sonnet ($0.10/MTok) and Opus
($0.20/MTok), checked against the official pricing table on 2026-10-28.
5-minute writes
cost 1.25×, 1-hour writes 2×. Ordinary input, reads and writes are disjoint
counts, so cached tokens are not charged again as ordinary input. The API's
per-TTL write breakdown takes precedence; when absent, the requested TTL is
used. Unknown models or malformed/inconsistent counts leave the estimate
unavailable. Charged refusals, long-input tiers and fallback can change billing.
A character limit does not guarantee a token tier. Account access, billing,
rate limits and real latency remain unverified; activation needs owner approval.

API contract checked 2026-10-27 against official [model IDs](https://platform.claude.com/docs/en/models/overview),
[effort](https://platform.claude.com/docs/en/build-with-claude/effort),
[refusals/fallback](https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback),
[Haiku tiers](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
and [Python SDK](https://github.com/anthropics/anthropic-sdk-python).
Mocked SDK tests bind arguments to the installed 2.3.0 stream signatures, and
exercise real engine error persistence. No real provider or local inference.
See the [delivery case](../delivery_tests/ask-claude.json) and the
[unexecuted JSON-check example](../../examples/ask_hosted_question.json).
`aotn build examples/ask_hosted_question.json --check` validates that example
without saving or calling the API.

Caching checked 2026-10-28 against installed SDK **2.3.0**
`TextBlockParam`, `CacheControlEphemeralParam` (`type="ephemeral"`,
`ttl="5m"|"1h"`), `Usage` / `BetaUsage` and `CacheCreation`. Rates follow the
[official caching pricing](https://platform.claude.com/docs/en/about-claude/pricing)
and [cache guide](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).
Mock tests cover both stream routes, unchanged off requests, cache prefix reuse,
TTL pricing, Options persistence, fallback usage and sanitized real-engine run
history. No real API calls or owner Secrets were accessed for this change.
