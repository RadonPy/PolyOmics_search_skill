# Observed Sim2Real Evidence contract

Observed 2026-11-26 (JST) via anonymous Streamable HTTP at the endpoint in
`mcp.json`. MCP protocol `2025-11-25`; eight tools; no Evidence output schema
advertised. Successful Evidence calls return a JSON `ok` envelope.

| Tool | Observed inputs |
|---|---|
| `get_sim2real_catalog` | Optional `property_query`, `include_properties`, `include_metric_definitions`, `locale` |
| `search_sim2real_evidence` | Optional `evidence_type`, `md_property_id`, `experimental_property_id`, `pretraining_property_id`, `population_id`, `sort_by`, `limit`, `cursor`, `filters` |
| `get_sim2real_evidence` | Required `evidence_id`, optional `detail_level` and `evidence_revision` |

Search returns `items[]`, `offset`, `total_matches`, `next_cursor` and
`property_resolutions`; detail returns `record`. Property IDs are canonical
and aliases are explicit. Catalog gives axis semantics in
`available_evidence_types.<type>` and definitions in
`metrics_registry.metric_availability.<type>.<metric>`. For known fit fields,
the fit definition may identify scope/method even without a `category`.

| Field path in detail | Meaning |
|---|---|
| `record.linear_fit_a/b/r2/n_pairs/method/status` | Flat nullable fit values, positive integer fit count, method and status. Actual observations used `ols_with_intercept` and `ok`. Separate from `record.r2` and from Source MD metrics. |
| `record.linear_fit.{formula,a_unit,b_unit,scope,is_validated_calibration}` | Published descriptive Y = a X + b, Y/X and Y units, no validated calibration. |
| `record.{x_origin,y_origin,x_unit,y_unit}` | Direct: MD vs observed experiment. Indirect adds Source-only comparison, canonical source/target IDs and `trained_on_experimental_target_labels=false`. Catalog declares pairing on the same structure. |
| `record.source_member_validation` | Summary/detail of a separate `model_validation` record. Join by its explicit Evidence ID, `related_source_model_id` and `validated_property_id`. The member set has its own `model_id`. |
| `record.source_model_validation_evidence_id` and `record.source_model_validation` | Independent Source-model evaluation, separate from members. Both null in the inspected release; no independent live example. |
| Member `evaluation_mode`, `evaluated_model_scope`, `evaluation_protocol_id`, `n_seeds_*`, `seed_coverage_fraction`, `seedwise_n_test_*`, `<metric>_<stat>`, `<metric>_n_seeds` | Individual archived MD model diagnostics with named units in `seedwise_metric_units`; test sets can overlap. Legacy single-evaluation fields are null. Member independence is not ensemble independence. |
| `record.study`, `record.population`, `record.notes`, `record.applicability`, `record.warnings` | Public citations, scope, and cautions. Null is unreported, never zero. |

Observed API contract `1.0`, schema `1.5.0`, release
`public:sim2real-v1.5:a42a5f0eccfbea1e8f0d3f7b`. The immutable
`evidence_dataset_revision` and `evidence_revision` were
`bb3d44752a855b621b461408ed93c77a3614b6e0`. The source MD revision
`polyomics_data_revision` is `not_recorded`; this is neither the Evidence
file commit nor the current MD tool's `dataset_revision`. Version/identity
are checked across calls; this particular release ID is not a requirement.
Direct and Indirect fits and a member aggregate were observed; unavailable
fits and independent links with data are covered with synthetic tests.
