# Changelog

## 1.3.1 — 2026-11-19

- Separate a matching source MD validation record from usable numeric holdout performance. Require a positive test size and a valid performance metric.
- Read registered metric definitions from Catalog or a supplied registry. Keep model validation and association errors separate, and check declared basis, units, and signed-error definitions.
- Replace the packaged icon with the supplied PNG, retain the original bytes in the plugin ZIP, and use a transparent square variant for display. Read ZIP inputs as bytes and validate both icons.

## 1.2.0 — 2026-11-19

- Initial packaged PolyOmics Search skill and remote MCP connection over the existing repository's license commit.
- Added live public MD search, detail and cohort workflows, with a fallback while evidence tools are not deployed.
- Implemented the v1.2 consumer rules: accept only source-surrogate-predicted MD(A) versus measured experimental(B) for indirect association; reject the withdrawn target-prediction axes. Match linked source MD holdout validation separately and report defined association errors only on their published scale.
- Added synthetic contract tests, reproducible release archives, CI configuration and public MCP verification tooling.
