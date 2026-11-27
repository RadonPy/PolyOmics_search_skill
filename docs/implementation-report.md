# Implementation and verification

## Proactive Sim2Real reasoning, v1.6.0

The feature branch `codex/proactive-sim2real-reasoning` starts from `main` at `a6cf7f892c4cc350fc9db7f1a81fa5b013d881e8`. The tracked checkout matched the v1.5.0 source, including the merged workspace packaging. The 155 baseline tests passed. A pre-existing untracked icon stayed outside the change.

### Scientific policy

The Skill proactively seeks Evidence for experimental targets and application screening. An eligible public Direct fit and compatible candidate yield a labeled exploratory experimental point estimate. This replaces the historical blanket ban on applying a public fit. Existing privacy safeguards continue to exclude private PoLyInfo measurements, pairs, membership, private predictions, models and reconstruction through slicing. When the fitted Source prediction is unavailable, a relevant signed association can support a qualified proxy. Exact-predictor Indirect estimates require verified model identity, revision, aggregation, preprocessing, scale and permitted use. A separately validated bridge is a possible future route. The deployed tools exposed no candidate Source predictor or bridge.

Reportability, candidate applicability and independent experimental validation remain distinct. Seed-wise member diagnostics and an independent Source MD holdout, when released, describe MD tasks. Neither establishes validation of the experimental mapping. Synthetic tests cover an eligible density fit, `0.9 × 1.50 + 0.1 = 1.45 g/cm³`, unknown-domain conditional estimation, and exploratory Indirect math with an exact synthetic Source predictor. Structural, provenance, policy, scale and quality gates block incompatible calculations.

The public Evidence manifest and README describe an aggregate-only distribution. The catalog's data-access statement describes what the service returns. It does not release individual labels, Source predictions, or model inference. The fit's descriptive scope conveys scientific limitations. The requested bounded use of authorized public aggregates remains subject to each source's terms. No underlying experimental-data rights were assumed. The present release does not supply fitted predictor ranges, calibrated prediction intervals, or an independent experimental mapping for the checked examples. [Public MD terms](https://huggingface.co/datasets/yhayashi1986/PolyOmics) · [Pinned Evidence README](https://huggingface.co/datasets/yhayashi1986/PolyOmics/blob/bb3d44752a855b621b461408ed93c77a3614b6e0/sim2real_evidence/releases/1.5.0/a42a5f0eccfbea1e8f0d3f7b/README.md)

### Listing copy

The new subtitle is **Polymer property database (MD)** at 30 characters. The historical v1.5.0 subtitle was “Search polymer simulations.” The agent uses the same new subtitle and the prompt “Use $polyomics-search to screen polymers for an application and assess published Sim2Real evidence.” The MCP dependency describes the read-only database and aggregate Evidence. The workspace profile retains the agent interface and uses its registered app binding. The full Skill description now defines the public simulation-derived property database and the proactive workflow. The identity, display name, endpoint, icons and read capability remain stable.

**Root description**

> Search PolyOmics, a large-scale computational polymer property database based on molecular simulations. Screen polymer candidates and use published Sim2Real evidence to estimate experimental properties and reason about material performance.

**Long description**

> Search PolyOmics, a large-scale computational polymer property database based primarily on all-atom molecular dynamics (MD). Find, rank, and compare polymers by simulated properties, polymer classes, and chemical structures. Use applicable published Sim2Real evidence for exploratory experimental-property estimates, simulation-based proxies, and evidence-guided materials design. Distinguish these estimates from measured experimental values and independently validated predictions.

See the [installation update steps](installation.md), [workspace update steps](web-compatibility.md#build-upload-and-install-the-workspace-zip), and [manifest](../plugin.json).

### Verification and release gates

| Status | Result |
|---|---|
| `CODE_READY` | 233 tests passed with no failures or skips. The official Agent Plugins schemas, Skill frontmatter, current listing metadata in all profiles, archive contents and links, and English checks passed. Synthetic forward tests covered application intent, conditional Direct arithmetic, private-data boundaries and MD-only queries. |
| `MCP_LIVE_VERIFIED` | On 2026-11-28 JST the strict anonymous SDK check passed 13 groups across eight tools and 20 calls with MCP protocol `2025-11-25`. All five original MD input schemas matched. Evidence schema `1.5.0`, API `1.0`, release `public:sim2real-v1.5:a42a5f0eccfbea1e8f0d3f7b`. The twelve-call applicability check below used the same release and current MD snapshot. |
| `WEB_E2E_NOT_VERIFIED` and `PLUGIN_METADATA_UI_NOT_VERIFIED` | The real workspace ZIP was generated, schema-validated and reproduced locally with the supplied app binding. The browser was signed out and the available-workspace lookup did not expose a matching connection from this session. Work, ordinary Chat and the installed listing await testing in the intended workspace. Raw connector calls exercised the MCP app. The new full plugin was not exercised in interactive Web or Desktop. |
| `PUBLIC_SUBMISSION_BLOCKED` | Public submission remains a separate owner workflow. The live service still lacks explicit tool annotations, and publication prerequisites include policy metadata, domain proof, dashboard scans, and an authorized walkthrough. [Review status](public-submission.md) |

**Live Direct results.** The SDK fetched real public polyimide candidates and successful published fits. The density comparison used 419 pairs with compatible unit spellings, but `definition_compatibility` is `unknown`. The 10 GHz Dk comparison has 13 pairs and an explicit zero-humidity extrapolation condition. The public candidate field had no verified unit or 10 GHz mapping in the MCP field catalog. The checks withheld numerical estimates in both cases. The fitted X domain was absent and the original MD revision was `not_recorded`. The current MD and Evidence storage revisions both happened to be `bb3d44752a855b621b461408ed93c77a3614b6e0`.

**Live Indirect result.** The fitted relation for Source thermal conductivity versus measured water absorption used 321 pairs. Its Source-predicted X makes observed MD ineligible for the equation. The proxy-only route was verified against the actual public record and member link. Member metrics were reportable, with unknown independence. The independent Source MD link and independent experimental validation were unavailable. Any direction remains a hypothesis unless source-to-observed transfer is scientifically justified. [Sanitized SDK receipt](live-mcp-proactive-sim2real.json)

| Public artifact | SHA-256 |
|---|---|
| [Standalone Skill](../dist/skill.zip) | `25813439a5622e25e0da04415d6d26a1b8b30a272395bf56863553f67474a6e4` |
| [Portable plugin](../dist/polyomics-search-plugin.zip) | `d1e287a502480ab17280fc12b88c168956c0d09f03b07732009a2e85a590f6eb` |

The two public ZIPs reproduced byte for byte. The workspace ZIP was checked with both synthetic and supplied bindings. The actual workspace binding and ZIP are private local files. Changes cover the Skill and its four references, optional inference helper, plugin and agent metadata, package validator, estimation and metadata tests, release archives, installation and verification guides, and the sanitized SDK receipt. Existing server and CI configuration stay in place.

```sh
python -m pytest -q
python scripts/package_releases.py --profile portable
python scripts/validate_package.py --profile portable --schema-dir .cache/schemas
python scripts/package_releases.py --profile workspace
python scripts/validate_package.py --profile workspace --schema-dir .cache/schemas
python scripts/check_english_text.py --archive .local/dist/polyomics-search-web-plugin.zip
python scripts/check_live_mcp.py --smarts --evidence require --output .cache/live-mcp-proactive-sim2real.json
git diff --check
```

The direct live numerical example remains blocked by incomplete applicability metadata. A real Source predictor or verified bridge, published predictor domain/uncertainty and independent experimental mapping validation would extend future use. See the [host acceptance cases](evaluation-cases.md) for the remaining deployment tests.

## Web distribution, v1.5.0 (historical)

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
