# 実装と検証結果（2026-11-19）

Skill / Plugin `polyomics-search` 1.2.0。既存のRadonPy BSD 3-Clauseライセンスを保持し、Skill、Agent Plugins 1.0.0マニフェスト、MCP設定、文書、CIワークフロー、再現可能な配布ZIPを追加しました。Sim2Realはクライアントの解釈を先行実装しました。

| 範囲 | 結果 |
|---|---|
| `python -m pytest -q` | PASS：29件。v1.2合成フィクスチャ、役割・版・構造の検査、旧Indirect Evidence拒否、再現可能なZIP |
| Skill validator / Agent Plugins 1.0.0公式JSON Schema / ZIP内容 | PASS |
| `python scripts/check_live_mcp.py --smarts` | PASS：匿名アクセス、5ツール、UUID詳細と集計の照合、入力エラー。ポリイミド＋密度条件に1,265件、SMARTS追加時に1,195件 |
| Sim2Real本番E2E | NOT RUN：現行MCPにEvidence 3ツールが未提供 |
| ChatGPT上のプラグイン検証 | BLOCKED：非公開登録の試行はHTTP 403。ワークスペースでMCP付きプラグインの利用権限が必要 |
| GitHub Actions | NOT RUN：ローカル検証とリモートCIは別 |

GitHub `main` は公開アクセスで `30871c2eba6ca21165d165f0fa539aed1d9087ab`（ライセンスのみ）を取得済みです。作業ブランチは `codex/polyomics-search-v1-2`。GitHubへの書き込みはリポジトリの公開設定とは別に認証と権限が必要です。

実行記録は [live-mcp.json](live-mcp.json)、再現手順は[開発とテスト](developer-testing.md)。実物のPoLyInfoレコード、個別予測、モデル重み、秘密情報、個人固有のプラグイン登録情報は配布対象に含みません。
