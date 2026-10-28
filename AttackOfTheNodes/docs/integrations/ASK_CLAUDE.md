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
is Vault only: model that served the reply, input/output tokens, stop reason,
wall seconds and a USD **Estimate**. It contains no question, Context, thinking,
SDK exception body or API key. Answer masks only exact known Secrets values;
ordinary labels such as `key`,
`token` and `password_hint` remain data. JSON mode parses first, masks decoded
strings (including object keys), then serializes valid JSON text. SDK diagnostics
and Run details retain the shared credential redactor (labels plus known Secrets).
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
($0.50 / $2.50); caching, charged refusals and fallback can also change billing.
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
