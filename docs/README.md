# docs

このディレクトリは、`twin-layer-brain-template` の人間向け運用ドキュメントです。
全体の入口は repo root の [README.md](../README.md) です。

| ファイル                                       | 読むタイミング                                             |
| ---------------------------------------------- | ---------------------------------------------------------- |
| [template-operation.md](template-operation.md) | template repo 自体を保守する時                             |
| [instance-setup.md](instance-setup.md)         | template をコピーして新しい brain を作る時                 |
| [environment.md](environment.md)               | `.env` と環境変数の優先順位・用途・既定挙動を確認する時    |
| [knowledge-ingest.md](knowledge-ingest.md)     | ソースを取得し、wiki に取り込む時                          |
| [chrome-extension.md](chrome-extension.md)     | Chrome から Web clip を保存する時                           |
| [search.md](search.md)                         | SQLite / LLM Wiki の検索の使い分けを確認する時             |
| [http-api.md](http-api.md)                     | HTTP server / REST API の起動・認証・endpoint を確認する時 |
| [server-management.md](server-management.md)   | macOS / Linux の HTTP server 常駐運用を確認する時          |
| [mcp.md](mcp.md)                               | MCP server の起動方法と tool を確認する時                  |
| [wiki-operations.md](wiki-operations.md)       | query / sublime / dive / lint の運用を確認する時           |
| [mise-tasks.md](mise-tasks.md)                 | `mise run ...` の意味と使い分けを確認する時                |

設計思想は [../development/architecture.md](../development/architecture.md) に分けています。
