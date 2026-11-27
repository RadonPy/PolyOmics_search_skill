# Privacy and data sources

| Data | Handling |
|---|---|
| Public PolyOmics MD | The MCP searches records and aggregates from the [published dataset](https://huggingface.co/datasets/yhayashi1986/PolyOmics). Follow the dataset card for citation and data licensing. |
| Published Sim2Real aggregates | Use authorized public aggregate equations for bounded exploratory estimates on compatible candidate inputs. Label those values as newly derived, with their evidence and limits. |
| Individual PoLyInfo measurements, private matches or membership, private surrogate outputs and model weights | Keep them outside retrieval, reconstruction, estimation of hidden labels, and disclosure. Arbitrary narrow or complementary slicing is outside the public workflow. |
| Synthetic examples | Used exclusively in offline tests. |

Search parameters, including SMILES, SMARTS, and property thresholds, go through the host and the public Hugging Face MCP service. The respective service terms apply. Use public structures and omit credentials from query inputs. The source license governs the code. Scientific datasets and experimental data have separate rights. [Source license](../LICENSE)

The dataset card identifies public PolyOmics MD data as CC BY 4.0. The Evidence release describes a public aggregate distribution and retains the original source terms. Respect any explicit restriction on numerical use and any prohibitions on redistributing or reconstructing private experimental data. A public aggregate inspection does not confer rights to the underlying PoLyInfo or literature records. [PolyOmics dataset card](https://huggingface.co/datasets/yhayashi1986/PolyOmics) · [Public Evidence distribution](https://huggingface.co/datasets/yhayashi1986/PolyOmics/tree/main/sim2real_evidence)

This page describes data handling. It does not claim a retention period or stand in for owner-approved privacy and terms URLs required by the public directory.
