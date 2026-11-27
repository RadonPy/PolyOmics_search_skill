# Changelog

## 1.6.0 — 2026-11-28

- Retrieve Sim2Real Evidence proactively for experimental-property, application and design requests while preserving simulation-only searches.
- Support bounded exploratory experimental estimates from eligible public Direct fits. Use Indirect associations as signed proxies when the exact authorized predictor is unavailable. Keep private records and reconstruction outside the workflow.
- Clarify the database identity in listing and Skill metadata with the subtitle **Polymer property database (MD)** and updated starter prompts across package profiles.
- Add deterministic estimation, applicability, and package metadata checks while preserving Evidence schema 1.5.0 and earlier interpretation behavior.

## 1.5.0 — 2026-11-26

- Generate a workspace Web ZIP that binds a registered PolyOmics cloud app. Keep the existing standalone Skill and portable remote-MCP ZIP.
- Document workspace installation, Web acceptance checks, and the separate public directory review route.
- Standardize repository and release text in English while keeping the Skill's multilingual response instructions.
- Check archive contents, English text, and local Markdown links in CI. Include service identity and tool annotations in live MCP receipts.

## 1.4.0 — 2026-11-26

- Support public Sim2Real 1.5.0 Direct and Indirect OLS fits, with fit status, axes, units and sample checks.
- Separate seed-wise member diagnostics from independent Source MD validation. Preserve the legacy holdout and registry behavior.
- Add strict anonymous Evidence verification to the live checker and optional CI run; preserve the MD schema baseline.

## 1.3.1 — 2026-11-19

- Separate a matching source MD validation record from usable numeric holdout performance. Require a positive test size and a valid performance metric.
- Read registered metric definitions from Catalog or a supplied registry. Keep model validation and association errors separate, and check declared basis, units, and signed-error definitions.
- Replace the packaged icon with the supplied PNG, retain the original bytes in the plugin ZIP, and use a transparent square variant for display. Read ZIP inputs as bytes and validate both icons.

## 1.2.0 — 2026-11-19

- Initial packaged PolyOmics Search skill and remote MCP connection over the existing repository's license commit.
- Added live public MD search, detail and cohort workflows, with a fallback while evidence tools are not deployed.
- Implemented the v1.2 consumer rules: accept only source-surrogate-predicted MD(A) versus measured experimental(B) for indirect association; reject the withdrawn target-prediction axes. Match linked source MD holdout validation separately and report defined association errors only on their published scale.
- Added synthetic contract tests, reproducible release archives, CI configuration and public MCP verification tooling.
