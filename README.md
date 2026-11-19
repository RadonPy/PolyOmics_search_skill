# PolyOmics Search Skill / Plugin

PolyOmicsの公開分子動力学（MD）データを検索・比較し、公開されたSim2Real集計が利用できる場合に解釈するためのSkillと、既存のPolyOmics MCPに接続するプラグインです。**現行MCPの提供機能はMD検索の5ツールです。Sim2Real evidence APIは未デプロイです。**

| 配布物 | 内容 |
|---|---|
| [skill.zip](dist/skill.zip) | スタンドアロンSkill。MCPはクライアント側で設定します。 |
| [polyomics-search-plugin.zip](dist/polyomics-search-plugin.zip) | Agent Plugins 1.0.0準拠のSkill＋MCP接続。 |

[インストール](docs/installation.md) · [MCP互換性](docs/mcp-compatibility.md) · [開発とテスト](docs/developer-testing.md) · [実装と検証結果](docs/implementation-report.md)

試す例：「PolyOmicsで密度1.3 g/cm³以上のポリイミドを、熱伝導率が高い順に3件探して。データのリビジョンと単位も示して。」

English example: “Find three PolyOmics polyimide runs with density at least 1.3 g/cm³, sorted by simulated thermal conductivity. Include units and the source revision.”

将来のv1.2 Indirect Evidenceは、同一ポリマー構造で私的に対応付けた**ソースモデルが予測したMD物性Aと、実測した実験物性B**の公開集計です。ソースモデル自体の検証対象は保持されたMD(A)であり、Bの実験予測精度とは別です。直接比較は観測MD(A)と実測実験(A)です。公開集計から個別の実験値や予測値は得られません。APIが未公開の間も、公開MD検索と仮説の整理は可能です。

新しい承認済み集計や指標は、同じツール・意味の契約内ならライブCatalogから取得します。v1.1からv1.2への軸変更のような意味の変更、Skill自体の編集、接続URL、認証やツール形式の変更には配布物の更新が必要です。

出典: [PolyOmicsデータセット](https://huggingface.co/datasets/yhayashi1986/PolyOmics) ([データDOI](https://doi.org/10.57967/hf/7475))、[PolyOmics論文](https://doi.org/10.48550/arXiv.2511.11626)、[MCP Space](https://huggingface.co/spaces/yhayashi1986/PolyOmics_MCP)。ソースコードは既存の[BSD 3-Clauseライセンス](LICENSE)に従います。データ利用条件は[データの扱い](docs/privacy-and-data-sources.md)を参照してください。
