# Public directory submission preparation

**Status: `PUBLIC_SUBMISSION_BLOCKED`.** The portable candidate and review cases are prepared. Public submission still requires a verified publisher and portal access, owner-approved listing links, MCP tool annotations and justifications, successful domain verification and dashboard scans, a reviewer-accessible walkthrough, and owner sign-off. A private workspace installation has its own [setup and acceptance process](web-compatibility.md).

## Package and listing

- In the developer dashboard, use the **With MCP** flow. The portable archive contains the portable manifest, the shared Skill, and one anonymous Streamable HTTP MCP definition. The portal discovers the connection from the configuration and may need the endpoint confirmed in the dashboard. Preserve `polyomics-search` for an existing compatible listing. If an existing skills-only listing cannot accept an MCP connection, obtain owner approval before any migration. [Portable plugin archive](../dist/polyomics-search-plugin.zip)
- Use **PolyOmics Search** as the display name, **Search polymer simulations** as the subtitle, and **Scientific Research** as the category. The plugin searches public simulations and interprets published aggregate Sim2Real evidence. The existing listing prompts cover polyimide ranking and comparison. The included 288 × 288 RGBA PNG is 24,577 bytes.
- The repository and Hugging Face Space links identify the project. The submitting organization must approve the public website, support contact or URL, privacy policy, and terms of service. Select the verified publisher identity in the dashboard. The [data sources and privacy notes](privacy-and-data-sources.md) describe the data boundary and code license.
- Release notes for v1.5.0 describe a shared, English-language Skill, multilingual responses, and continued support for Sim2Real Evidence 1.5.0. The workspace ZIP uses a separate distribution route.

See the [submission flow](https://developers.openai.com/plugins/deploy/submission) and [validation requirements](https://developers.openai.com/plugins/deploy/submission-errors).

## Remote server and domain

The [production MCP receipt](live-mcp-web-compatibility.json) confirms anonymous calls to all eight tools. The service advertises no explicit `readOnlyHint`, `destructiveHint`, or `openWorldHint` on any of those tools. The dashboard requires explicit values and justifications for each. The proposed annotations for these read operations are `readOnlyHint: true`, `destructiveHint: false`, and `openWorldHint: false`. The server maintainer should verify that each scope holds, expose the annotations, and rescan before submission.

| Tools | Proposed justification |
|---|---|
| `get_dataset_info`, `list_search_fields` | Return metadata for the configured public PolyOmics dataset. No write action, user data, or arbitrary destination is accepted. |
| `search_polymers`, `get_polymer`, `aggregate_polymers` | Query or summarize the configured public MD records with bounded inputs. They do not update stored records or access arbitrary external resources. |
| `get_sim2real_catalog`, `search_sim2real_evidence`, `get_sim2real_evidence` | Read a named public Evidence release and its approved aggregate fields. They do not mutate records or retrieve data from a user-supplied destination. |

On 2026-11-26 the Space's `/.well-known/openai-apps-challenge` path returned HTTP 200 with a Gradio HTML page, so the deployed response does not serve a plain-text challenge. Whether the Space can host the exact dashboard-issued token at its HTTPS origin requires a server-side change and a rerun of the challenge. The owner should first confirm that the portal accepts the Space hostname. Do not rely on control of the shared `hf.space` parent domain. If the Space hostname is ineligible, use a separately authorized controlled origin and confirm that the challenge and MCP handshake both work there. [OpenAI domain requirements](https://developers.openai.com/plugins/deploy/submission#domain-verification-details)

## Cases for review

These are draft review cases. Execute them in the actual review surface before submission and include a walkthrough recording. The MCP client receipt covers the protocol and representative data operations.

| Positive case and prompt | Expected tools | Expected behavior |
|---|---|---|
| What is the live PolyOmics data revision, and which fields can I search? | `get_dataset_info`, `list_search_fields` | Cite the live revision and field types and units. |
| Find three dense polyimides and compare their thermal conductivity using PolyOmics. | `list_search_fields`, `search_polymers`, `get_polymer` | Return a bounded cohort with MD values, units, and source links, or a clear empty result. |
| Summarize simulated thermal conductivity for the same polyimide filter. | `list_search_fields`, `aggregate_polymers` | Give a cohort summary with the applied filter, sample size, and scope. |
| Retrieve Direct Evidence for Abbe number. Explain the fit, sample count, caveats, and citation. | `get_sim2real_catalog`, `search_sim2real_evidence`, `get_sim2real_evidence` | Verify the actual axes and finite coefficients when available, distinguish agreement from fitted R², and cite the release. |
| Find an Indirect Evidence record with member validation and describe what independent validation is available. | `get_sim2real_catalog`, `search_sim2real_evidence`, `get_sim2real_evidence` | Preserve the source and target directions. Separate member diagnostics from independent evaluation and acknowledge any missing link. |

| Negative case and prompt | Expected behavior |
|---|---|
| Give me the private experimental measurements and predictions used to fit an Indirect Evidence record. | Explain that individual values and predictions are unavailable, and offer the published aggregate details. |
| Correct this polymer's record in the PolyOmics dataset. | Explain the read-only scope and avoid attempting a data mutation. |
| Show the regression for the nonexistent Evidence ID `unknown-review-record`. | Report the missing record and avoid fabricating coefficients. Offer a catalog search. |

After the portal accepts the candidate, complete the policy attestations and owner review. Approval and publication are separate steps. Publish only with explicit authorization.
