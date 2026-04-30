# CHANGELOG

すべての注目すべき変更はこのファイルに記録されます。

フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づいており、
このプロジェクトは [Semantic Versioning](https://semver.org/lang/ja/) に準拠しています。

## Tagged Releases

- [unreleased](https://github.com/Seika139/twin-layer-brain-template/compare/v0.1.0...HEAD)
- [0.1.0](https://github.com/Seika139/twin-layer-brain-template/releases/tag/v0.1.0)

## [Unreleased]

## [0.1.0] - 2026-05-01

### Added

- **二層アーキテクチャ**
  - SQLite FTS5 + sqlite-vec を使った高速検索層 (Layer 1) と、LLM が `[[wiki-link]]` で育てる Markdown wiki 層 (Layer 2) を統合した知識ベーステンプレート
  - Markdown を単一の真実のソースとし、`kc index` で SQLite を再生成するワンウェイ・データフロー
- **`kc` CLI** ([compiler/cli.py](compiler/cli.py))
  - `new` / `index` / `validate` / `search` / `show` / `suggest-related` / `status` / `check-keys` サブコマンドを提供
  - `kc validate` で frontmatter の YAML parse error を機械的に検出
  - `kc status` で index DB サイズ / note 件数 / embedding カバレッジを要約表示
- **HTTP / MCP server** ([server/](server/))
  - FastAPI による REST API と MCP server を提供（token 認証、外部 LLM クライアントから検索可能）
  - `mise run serve` で foreground 起動、`mise run serve-install` で macOS launchd 登録
  - Linux systemd / macOS launchd / Caddy 用の deploy 設定 ([deploy/](deploy/))
- **Chrome 拡張 (web clipper)** ([chrome-extension/](chrome-extension/))
  - 開いているページを LLM 要約付きで `raw/articles/` に保存する web clipper
- **LLM skills** ([.agents/skills/](.agents/skills/) / [.claude/skills/](.claude/skills/))
  - `ingest` / `query` / `dive` / `lint` / `sublime` の 5 種類を Claude Code / Codex CLI 両対応で配置
  - `mise run skills` で `.agents/` を真のソースとして `.claude/` へ real-file copy で同期
- **Wiki 構造** ([wiki/](wiki/))
  - `sources/` / `entities/` / `concepts/` / `topics/` / `analyses/` に分割し、`wiki/index.md` と `wiki/log.md` の自動メンテナンス契約を定義
  - YAML frontmatter (`title` / `type` / `created` / `updated` / `sources` / `tags`) の規約
- **`repos.json` マニフェスト** ([repos.json](repos.json))
  - `raw/repos/` の clone 対象を宣言的に管理し、`mise run clone-repo` / `mise run update-repos` で別マシンでも同じ状態を再現可能に
- **mise tasks** ([mise.toml](mise.toml) / [mise/tasks/](mise/tasks/))
  - `init` / `lint` / `format` / `test` / `serve` / `kc` / `status` / `validate` / `check-keys` / `scaffold-brain` / `diff-template` などを提供
  - `BRAIN_ROOT` 環境変数でリポジトリルートを上書き可能に
- **CI / lint パイプライン**
  - GitHub Actions: `lint-markdown` / `lint-yaml` / `shellcheck` / `update-version` / `uv-qualify` ([.github/workflows/](.github/workflows/))
  - ローカル lint / format で `rumdl` / `markdownlint-cli2` / `ruff` / `mypy` / `shfmt` / `shellcheck` / `yamllint` / `taplo` を統合
