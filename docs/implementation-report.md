# Implementation and verification

## Web distribution, v1.5.0

The `codex/polyomics-chatgpt-web` branch starts from `a0bff1ce24e35ba0cdbe0c68932b72ac86cd26d8`. That merge includes the first v1.5-compatible plugin implementation. The current release preserves the scientific workflows, remote endpoint, and icon bytes. The Web workspace profile binds a registered app and uses the same scientific Skill instructions as the portable profile.

| Status | Verification |
|---|---|
| `CODE_READY` | 155 offline tests passed, with zero failures or skips. Both public ZIPs are byte-identical across repeated builds. The Agent Plugins schemas, Skill validator, English text and archive checks, relative file links, and Git whitespace checks passed. The workspace test used a synthetic ID in a temporary directory and validated the generated manifest against the official schema. |
| `MCP_LIVE_VERIFIED` | On 2026-11-26 at 14:18 UTC, anonymous Streamable HTTP negotiated MCP `2025-11-25` with PolyOmics MCP Server `1.30.0`. Eight tools and 20 actual calls passed the 13 strict check groups. Five MD input schemas were unchanged. The test covered valid and invalid inputs, SMARTS, paging, aliases, provenance, finite Direct and Indirect coefficients, and member diagnostics. Independent validation was reported as `not_provided`, and the original MD revision in the evidence provenance was `not_recorded`. |
| `WEB_E2E_BLOCKED` | The user reported a ZIP installation. The target workspace's registered app ID and listing eligibility are unverified. The connector lookup was unavailable and the browser integration failed during startup with OS error 3. W1–W8 were not run. Existing Codex plugin tools returned the expected MD revision and Evidence release. An interactive installation test of the rebuilt portable plugin remains open. |
| `PUBLIC_SUBMISSION_BLOCKED` | The portable candidate and draft review cases are ready for owner review. The live server exposed none of the three required tool hints. The domain challenge path served Gradio HTML. A verified submitting identity, listing URLs, successful dashboard scans, a verified domain challenge, and a reviewer walkthrough are pending. |

The production dataset revision was `bb3d44752a855b621b461408ed93c77a3614b6e0` and the Evidence release was `public:sim2real-v1.5:a42a5f0eccfbea1e8f0d3f7b` with schema `1.5.0`. The receipt includes the release manifest hash and input schema fingerprints. [Production receipt](live-mcp-web-compatibility.json)

| Artifact | SHA-256 |
|---|---|
| [Standalone Skill](../dist/skill.zip) | `39c73b9ebc72aa4d2370524f9de715752eadddb21f332f9c365b224b480a7c9a` |
| [Portable plugin](../dist/polyomics-search-plugin.zip) | `5b50462f6886deb7e1f212191ab23e2d0ce8faccba2d05a44a9b23da1a57fdf0` |

The workspace archive is generated under `.local/dist/` when a real app ID is available. The code changes cover the package builder and validator, the plugin and Skill text, the strict live receipt, the English check, and CI. See the [Web setup and test cases](web-compatibility.md) and [public review requirements](public-submission.md).

Verification commands, using the development environment's Python:

```sh
python -m pytest -q --tb=short --basetemp=.local/pytest-web-final -p no:cacheprovider
python scripts/package_releases.py
python scripts/validate_package.py --schema-dir .cache/schemas
python scripts/check_english_text.py
python scripts/check_live_mcp.py --smarts --evidence require --output .cache/live-web-final.json
python -X utf8 /path/to/skill-creator/scripts/quick_validate.py skills/polyomics-search
git diff --check
```

## v1.4.0 — 2026-11-26 JST (historical)

- Added v1.5 Direct/Indirect fit validation, separate fitted and uncorrected R², and separate member and independent validation checks.
- The strict live check passed at 15:20 JST with eight tools and 20 calls, unchanged MD schemas, and release `public:sim2real-v1.5:a42a5f0eccfbea1e8f0d3f7b`. Member diagnostics were present. Independent evaluation was unavailable. Synthetic tests covered independent links and missing fits. [Historical receipt](live-mcp-v1.5.json)
- 122 tests passed with no skips. The two ZIP builds were identical. Agent Plugins 1.0.0 and Skill validation passed. No ChatGPT installation or answer verification was performed at that time.
- Historical SHA-256 for `skill.zip` was `f3abbc1cfe2b417c99fe51192ce9ac83094b55d76e70ea1a1e847c5e9296bee0`. The portable plugin hash was `691d5242dbdc71aac581c7a4cec0ef0018d9fafea712d70cbe645af7d32813a2`.

## v1.3.1 — 2026-11-19 (historical)

The local patch separated link matching and numeric availability, added registry-based metric checks, and updated the icon. Offline tests, ZIP validation, and Skill validation passed. No v1.3.1 ChatGPT installation or live Evidence check was performed.

## v1.2.0 — 2026-11-19 (historical)

Added the first Skill, portable manifest, MCP configuration, CI and reproducible distributions. The offline suite passed 29 tests. The [live MD check](live-mcp.json) passed all five tools with 1,265 filtered records and 1,195 after SMARTS. Evidence was not yet deployed. A private ChatGPT registration attempt returned HTTP 403 for MCP plugin access. Remote CI was not run in that implementation pass. The main branch then held only the license at `30871c2eba6ca21165d165f0fa539aed1d9087ab`, and write authorization was unavailable.
