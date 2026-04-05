# TechTrendWatcher 🚀

GitHubのトレンドリポジトリを自動で収集し、Notionで管理、Snowflakeで分析するデータパイプライン。

## 🎯 プロジェクトの目的
Pythonの高度な機能を活用し、実戦的なデータエンジニアリングスキルを習得する。
- 非同期処理による並列実行 (`asyncio`, `httpx`)
- 堅牢なバリデーションと型定義 (`Pydantic`)
- 高速なデータ加工 (`Polars`)
- 外部APIとの連携とレート制限・リトライ制御 (`tenacity`, Notion/Snowflake SDK)

## 🏗️ システムアーキテクチャ

### 1. Data Flow
1.  **Extraction**: `httpx` を用い、GitHub API から "GraphRAG" や "MCP" などの特定キーワードで非同期にリポジトリを検索。
2.  **Validation**: `Pydantic` で取得データをバリデーション。
3.  **Transformation**: `Polars` で前回データとの差分（Star増加数など）を計算。Snowflake用には `pyarrow` / `pandas` を経由して型を調整。
4.  **Loading**: 
    - **Snowflake (Silver Layer)**: `snowpark` を使用し、生データ (VARIANT) を含むトレンド情報をバルクロード。
    - **Notion**: 「今週の注目」リポジトリを自動でページ作成・更新（Upsert）。

### 2. 技術スタック & 学習トピック
- **Network**: `httpx` (Async HTTP Client)
- **Validation**: `Pydantic v2` (ConfigDict, Model Validator による生データ保持)
- **Data Processing**: `Polars` (DataFrame), `Pandas` (Snowpark連携用)
- **Database**: `Snowflake` (Snowpark SDK, write_pandas), `Notion API`
- **Infrastructure**: `uv` (Python package manager)
- **Async Strategy**: `asyncio.gather` (並列実行), `asyncio.to_thread` (同期SDKの非同期化)

## 🛠️ 開発ロードマップ
- [x] Phase 0: プロジェクトの初期化 & 環境構築
- [x] Phase 1: GitHub API 連携 (Async Search & Validation)
- [x] Phase 2: データバリデーション & Polars による差分計算
- [x] Phase 3: Notion / Snowflake 連携 (Loading)
    - [x] Notion データベースとの接続と Upsert ロジックの実装
    - [x] `asyncio.gather` による Notion 連携の並列実行
    - [x] Snowflake (Snowpark) へのバルクロード処理の実装
    - [x] **Engineering Challenges Overcome**:
        - `asyncio.to_thread` による Snowpark (同期) の非同期ラップ
        - `pyarrow` / `pandas` 依存関係の解消と型変換（TIMESTAMP_NTZ）
        - Pydantic モデルによる「生データ保持」と「フィルタリング」のトレードオフ解決
        - Snowflake 権限（USAGE/CREATE STAGE）と大文字小文字（Identifier）の制御
- [x] Phase 4: CI/CD & 定期実行の自動化
    - [x] GitHub Actions (`astral-sh/setup-uv`) による定期実行スケジュールの設定 (Cron)
    - [x] GitHub Secrets / Variables によるセキュアな認証情報管理（Notion/Snowflake/GitHub PAT）
    - [x] `uv run ttw` 用のエントリポイント整備と GitHub 仮想環境での動作確認
- [ ] Phase 5: 品質向上 & 堅牢化 (Engineering Excellence)
    - [x] **Testing**: `pytest` による網羅的テストの実装
        - [x] **Unit Tests**: `Processor` (star_delta計算) / `Models` (バリデーション/生データ保持) のテスト完了
        - [x] **Integration Tests**: `respx` を用いた `GithubClient` の異常系 (401, 429等) とリトライロジックの検証完了
        - [ ] **Integration Tests**: `NotionClient` の Upsert フローとエラーハンドリングの検証
        - [ ] **E2E Tests**: テスト専用環境 (Notion/Snowflake) を用いたパイプライン全体の疎通確認
        - [x] **Coverage**: 重要ロジック（GitHub連携・加工）のカバレッジ強化
    - [x] **Error Handling**: `tenacity` による高度なリトライ戦略（カスタム述語による500系/レート制限の選別、リトライログの可視化）
    - [x] **Static Analysis**: `Ruff` (Lint/Format) と `Mypy` (Strict Type Check) の導入、CIでの自動チェック体制構築
    - [x] **Documentation**: 全ての関数・クラスへの Type Hints 厳密化 (mypy strict) と Docstring 追加
    - [ ] **Observability**: JSON 形式の構造化ロギング導入と、処理件数・実行時間などのメトリクス計測
    - [x] **Engineering Excellence 修業 (completed)**:
        - `NotionClient` / `SnowflakeClient` における `return None` 方式の排除と、適切な例外 (`raise`) への移行
        - `isinstance(e, BaseError)` による例外の二重梱包（Wrapping）の防止
        - `main.py` における「プログラム停止（Critical）」と「クエリスキップ（Error/Warning）」の例外ハンドリング分離
        - `GithubClient` / `NotionClient` における `tenacity` を活用した「賢いリトライ」の実装

### 📅 次のタスク (Quality & Observability)
- [ ] **Testing**: `NotionClient` の統合テスト実装。特に `upsert_repo` の検索→更新/作成フローの検証
- [ ] **Observability**: 構造化ロギングへの移行と、Snowflake へのロード件数のメトリクス出力
- [ ] **Snowflake 連携の高度化**: `SnowflakeClient` での接続時エラーハンドリングのさらなる詳細化（エラーコード判別など）


## 🤝 Agent Interaction Policy
このプロジェクトでは、Gemini CLIを「単なるコード生成ツール」ではなく、「厳しいシニアエンジニア（メンター）」として扱います。
- **教育優先**: スキル向上のため、Agentによる直接のファイル修正は最小限に留め、コードレビューや設計のアドバイスを優先します。
- **コードの所有権**: 最終的な実装は必ず人間（mew）が行い、Agentの指摘を理解した上で反映させます。
- **ツンデレ・レビュー**: 厳しい指摘の中に愛（技術的妥当性）があることを理解し、プロフェッショナルなエンジニアを目指します。

