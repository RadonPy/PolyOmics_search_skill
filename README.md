# PolyOmics Search

![PolyOmics Search icon](assets/polyomics-square.png)

Search public PolyOmics molecular dynamics (MD) simulations and interpret published aggregate Sim2Real evidence. The shared Skill uses five MD tools and the three Sim2Real Evidence 1.5.0 tools when available. Ask questions in your own language.

| Distribution | Intended use | Prerequisite |
|---|---|---|
| [Standalone Skill](dist/skill.zip) | Compatible Skill runtimes | A separate PolyOmics MCP connection |
| [Portable plugin](dist/polyomics-search-plugin.zip) | Desktop, compatible portable hosts, and public remote-MCP submission preparation | A compatible host and MCP access. Direct import may be labeled Desktop only. |
| Workspace Web plugin | ChatGPT Web within a specific workspace | A registered PolyOmics cloud app, eligible workspace and role, and app access. [Build it locally](docs/web-compatibility.md). |
| Public directory plugin | Supported ChatGPT and Codex surfaces after publication | An approved, published listing and user eligibility. [Review preparation](docs/public-submission.md). |

[Installation](docs/installation.md) · [MCP compatibility](docs/mcp-compatibility.md) · [Development and tests](docs/developer-testing.md) · [Implementation results](docs/implementation-report.md)

Try: “Find three PolyOmics polyimide runs with density at least 1.3 g/cm³, sorted by simulated thermal conductivity. Include units and the source revision.”

Direct evidence compares MD and observed experiments for matched structures. Indirect evidence compares source-only predicted MD property A and measured experimental property B for the same structures. Published slopes, intercepts, and fitted R² describe the released aggregate. Member MD diagnostics are separate from independent evaluation of the source ensemble.

The [observed contract](docs/evidence-contract-v1.5.md) describes tool inputs and response shapes. The live catalog remains the source for current definitions, metrics, releases, and caveats. No package hosts another copy of the scientific data.

Use English for repository contributions, including instructions, examples, metadata, and test comments. Keep exact tool identifiers, citations, and scientific symbols. This policy does not restrict user queries or generated answers. Run the [repository check](docs/developer-testing.md) before submitting changes.

Sources: [PolyOmics dataset](https://huggingface.co/datasets/yhayashi1986/PolyOmics) ([dataset DOI](https://doi.org/10.57967/hf/7475)), [PolyOmics paper](https://doi.org/10.48550/arXiv.2511.11626), and [MCP Space](https://huggingface.co/spaces/yhayashi1986/PolyOmics_MCP). The source code follows the [BSD 3-Clause license](LICENSE). See [data sources and privacy](docs/privacy-and-data-sources.md) for data rights.
