# PolyOmics Search Skill / Plugin

![PolyOmics Search アイコン](assets/polyomics-square.png)

PolyOmicsの公開分子動力学（MD）データを検索・比較し、公開Sim2Real集計を解釈するためのSkillとプラグインです。**Plugin v1.4.0は、既存MD検索5ツールとSim2Real Evidence v1.5.0の3ツールに対応します。**

| 配布物 | 内容 |
|---|---|
| [skill.zip](dist/skill.zip) | スタンドアロンSkill。MCPはクライアント側で設定します。 |
| [polyomics-search-plugin.zip](dist/polyomics-search-plugin.zip) | Agent Plugins 1.0.0準拠のSkill＋MCP接続。 |

[インストール](docs/installation.md) · [MCP互換性](docs/mcp-compatibility.md) · [開発とテスト](docs/developer-testing.md) · [実装と検証結果](docs/implementation-report.md)

試す例：「PolyOmicsで密度1.3 g/cm³以上のポリイミドを、熱伝導率が高い順に3件探して。データのリビジョンと単位も示して。」

English example: “Find three PolyOmics polyimide runs with density at least 1.3 g/cm³, sorted by simulated thermal conductivity. Include units and the source revision.”

Indirect Evidenceは、同一構造で対応付けた**ソースモデルが予測したMD物性Aと、実測した実験物性B**の公開集計です。Directは対応構造のMD計算値と測定実験値を比較します。公開された傾き・切片・回帰R²を記述統計として扱い、回帰を個別実験値の推定に適用しません。member単位のMD診断とソースensembleの独立評価は別々に確認します。

新しい承認済み集計や指標は、同じツール・意味の契約内ならライブCatalogから取得します。v1.1からv1.2への軸変更のような意味の変更、Skill自体の編集、接続URL、認証やツール形式の変更には配布物の更新が必要です。

[実測した契約](docs/evidence-contract-v1.5.md)と[公開MCP検証結果](docs/live-mcp-v1.5.json)を参照してください。配布ZIPには従来の[PNG原本](assets/polyomics.png)と正方形アイコンを同梱します。

出典: [PolyOmicsデータセット](https://huggingface.co/datasets/yhayashi1986/PolyOmics) ([データDOI](https://doi.org/10.57967/hf/7475))、[PolyOmics論文](https://doi.org/10.48550/arXiv.2511.11626)、[MCP Space](https://huggingface.co/spaces/yhayashi1986/PolyOmics_MCP)。ソースコードは既存の[BSD 3-Clauseライセンス](LICENSE)に従います。データ利用条件は[データの扱い](docs/privacy-and-data-sources.md)を参照してください。
