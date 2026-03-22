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
- [ ] Phase 4: CI/CD & 定期実行の自動化
    - [ ] GitHub Actions による定期実行スケジュールの設定
    - [ ] 実行ログの管理とエラー通知の仕組み構築
- [ ] Phase 5: 品質向上 & 堅牢化 (Refactoring & Testing)
    - [ ] 独自例外クラスの導入と例外処理 (`try-except`) の徹底
    - [ ] `pytest` によるユニットテスト・統合テストの実装

## 🔑 環境構築
1. `uv sync`
2. `.env` ファイルの作成（GitHub, Notion, Snowflake の各認証情報）
3. `uv run ttw` で動作確認
