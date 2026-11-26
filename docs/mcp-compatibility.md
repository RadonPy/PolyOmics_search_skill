# MCP互換性

2026-11-26 JSTに、同じ匿名Streamable HTTP接続先で既存MD 5ツールとEvidence 3ツールを実呼び出ししました。MDの入力スキーマは[2026-11-19の基準](live-mcp.json)と一致します。Evidence schema 1.5.0 / API 1.0の引数とフィールドは[契約対応表](evidence-contract-v1.5.md)、strict実測結果は[検証ログ](live-mcp-v1.5.json)を参照してください。

## MD検索契約

2026-11-19 11:25 JST、認証なしで `https://yhayashi1986-polyomics-mcp.hf.space/gradio_api/mcp/` にStreamable HTTP接続し、MCP `initialize`（プロトコル `2025-11-25`）と `tools/list` を確認しました。検索・集計・UUID詳細の応答はリビジョン `dfd5053bc9e6976fba072f79567264771b9f5477`（176,096件）で一致しました。各入力スキーマのSHA-256は[実行記録](live-mcp.json)を参照してください。

| 実際のツール | 引数の形 |
|---|---|
| `get_dataset_info` | 引数なし |
| `list_search_fields` | 任意の `category`（`property`、`class`、`all`） |
| `search_polymers` | `request`：`property_filters`、`polymer_classes`、`class_logic`、`structure`、`text_filters`、`quality_filters`、`fields`、`sort`、`limit`、`cursor`、`include_total_count` など |
| `get_polymer` | `uuid`、任意の `fields` と `config` |
| `aggregate_polymers` | `request`：検索と共通のフィルター、`properties`、任意の `statistics`、`group_by`、`quantiles` |

応答は `ok` のあるJSONエンベロープです。検証では構造化コンテンツとJSONテキストを扱い、スナップショットとエラーコードを確認しました。`config` は `all_data`。密度は `g/cm³`、熱伝導率は `W/(m·K)`。SMARTSは `search_smiles` の有限グラフを対象とします。ツールの最新引数は毎回ライブスキーマを参照してください。

## Evidence

`get_sim2real_catalog`、`search_sim2real_evidence`、`get_sim2real_evidence` が利用可能です。API未提供、部分的な公開、空の公開データ、契約不一致、通信失敗は別の結果です。機能がなければMD検索または明示した仮説を使えます。旧v1.2の合成フィクスチャとローカルhelper入力は後方互換用で、現行のフィールドパスはライブ契約を参照してください。
