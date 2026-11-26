# Privacy and data sources

| Data | Handling |
|---|---|
| Public PolyOmics MD | The MCP searches records and aggregates from the [published dataset](https://huggingface.co/datasets/yhayashi1986/PolyOmics). Follow the dataset card for citation and data licensing. |
| Published Sim2Real aggregates | The MCP returns approved aggregate evidence. The Skill does not reconstruct individual values using narrow or complementary groups. |
| Individual PoLyInfo measurements, private matches and surrogate predictions, model weights and inference | The plugin does not distribute, retrieve, or reconstruct them. |
| Synthetic examples | Used exclusively in offline tests. |

Search parameters, including SMILES, SMARTS, and property thresholds, go through the host and the public Hugging Face MCP service. The respective service terms apply. Use public structures and omit credentials from query inputs. The source license governs the code. Scientific datasets and experimental data have separate rights. [Source license](../LICENSE)

This page describes data handling. It does not claim a retention period or stand in for owner-approved privacy and terms URLs required by the public directory.
