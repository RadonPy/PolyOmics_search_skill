# Changelog

## 1.2.0 — 2026-11-19

- Initial packaged PolyOmics Search skill and remote MCP connection over the existing repository's license commit.
- Added live public MD search, detail and cohort workflows, with a fallback while evidence tools are not deployed.
- Implemented the v1.2 consumer rules: accept only source-surrogate-predicted MD(A) versus measured experimental(B) for indirect association; reject the withdrawn target-prediction axes. Match linked source MD holdout validation separately and report defined association errors only on their published scale.
- Added synthetic contract tests, reproducible release archives, CI configuration and public MCP verification tooling.
