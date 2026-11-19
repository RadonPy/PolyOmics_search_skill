# MCP互換性

2026-11-19 11:25 JST、認証なしで `https://yhayashi1986-polyomics-mcp.hf.space/gradio_api/mcp/` にStreamable HTTP接続し、MCP `initialize`（プロトコル `2025-11-25`）と `tools/list` を確認しました。検索・集計・UUID詳細の応答はリビジョン `dfd5053bc9e6976fba072f79567264771b9f5477`（176,096件）で一致しました。各入力スキーマのSHA-256は[実行記録](live-mcp.json)を参照してください。

| 実際のツール | 引数の形 |
|---|---|
| `get_dataset_info` | 引数なし |
| `list_search_fields` | 任意の `category`（`property`、`class`、`all`） |
| `search_polymers` | `request`：`property_filters`、`polymer_classes`、`class_logic`、`structure`、`text_filters`、`quality_filters`、`fields`、`sort`、`limit`、`cursor`、`include_total_count` など |
| `get_polymer` | `uuid`、任意の `fields` と `config` |
| `aggregate_polymers` | `request`：検索と共通のフィルター、`properties`、任意の `statistics`、`group_by`、`quantiles` |

応答は `ok` のあるJSONエンベロープです。検証では構造化コンテンツとJSONテキストを扱い、スナップショットとエラーコードを確認しました。`config` は `all_data`。密度は `g/cm³`、熱伝導率は `W/(m·K)`。SMARTSは `search_smiles` の有限グラフを対象とします。ツールの最新引数は毎回ライブスキーマを参照してください。

`get_sim2real_catalog`、`search_sim2real_evidence`、`get_sim2real_evidence` は検出されませんでした。この状態ではSkillは存在しないエンドポイントを呼ばず、公開MD検索または明示した仮説のみを使います。Evidenceのデータが空、API未提供、旧意味論の提供、通信失敗は区別します。追加された場合は実際のCatalogと応答で軸と役割を検証してください。手元の合成データはライブの互換性を保証しません。
