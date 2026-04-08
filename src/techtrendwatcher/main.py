import asyncio
from typing import Any

import httpx

from techtrendwatcher.core.config import get_settings
from techtrendwatcher.core.exceptions import (
    ConfigurationError,
    GitHubAPIError,
    GitHubAuthError,
    GitHubRateLimitError,
    NotionAPIError,
    NotionAuthError,
    NotionRateLimitError,
    NotionResourceNotFoundError,
    NotionValidationError,
    SnowflakeAPIError,
    SnowflakeAuthError,
)
from techtrendwatcher.core.logger import get_logger, setup_logging
from techtrendwatcher.github.client import GithubClient
from techtrendwatcher.github.processor import (
    convert_to_dataframe,
    convert_to_silver_dataframe,
    get_trend_dataframe,
    save_as_parquet,
)
from techtrendwatcher.notion.client import NotionClient
from techtrendwatcher.snowflake.client import SnowflakeClient


async def main() -> None:
    # loggingの初期設定
    setup_logging()
    logger = get_logger(__name__)
    logger.info("pipeline_startup")

    # 各種.envの設定
    try:
        settings = get_settings()
    except ConfigurationError as e:
        logger.error("config_load_failed", error=str(e))
        return

    # httpクライアントの作成
    async with httpx.AsyncClient() as shared_client:
        # clientの作成
        client = GithubClient(shared_client)
        notion_client = NotionClient(shared_client)

        # セマフォの設定
        semaphore = asyncio.Semaphore(settings.notion_semaphore)

        async def limited_upsert(row: dict[str, Any]) -> None:
            async with semaphore:
                await notion_client.upsert_repo(row)

        for query in settings.search_query:
            """
            ここから一連の処理
            1. Githubからの取得
            2. 加工と保存
            3. Notionの更新
            4. Snowflakeのロード
            """
            logger.info("process_query_start", query=query)
            try:
                result = await client.search_github(query)

                # notiony用のgithub api responseをpolarsで処理
                co_git_api_res = convert_to_dataframe(result)

                # snowflake用のgithub api responseをpolarsで処理
                snowflake_git_search_to_pl = convert_to_silver_dataframe(result, query)
                logger.info(
                    "github_data_processed",
                    query=query,
                    count=len(snowflake_git_search_to_pl),
                )

                # githubのレスポンスをparquetで保存
                save_as_parquet(co_git_api_res, query)

                # 過去のレスポンスと比較し、スターに変更のあるものだけを検知
                trend_df = get_trend_dataframe(co_git_api_res, query)

                """
                Notionへの挿入
                """
                # Notionにすでにレコードがあるかチェックし、upsertを行う(並列実行)
                tasks = [limited_upsert(row) for row in trend_df.to_dicts()]
                await asyncio.gather(*tasks)
                logger.info("notion_upsert_completed", query=query, count=len(trend_df))

                """
                snowflakeへの書き込み
                """
                snowflake_client = SnowflakeClient(settings.snowflake)
                await snowflake_client.upload_to_snowflake(snowflake_git_search_to_pl)
                logger.info("snowflake_upload_success", query=query)

            except (GitHubAuthError, NotionAuthError, SnowflakeAuthError) as e:
                # tokenが不正
                logger.critical("auth_error_abort", error=str(e))
                return

            except (GitHubRateLimitError, NotionRateLimitError) as e:
                # リクエスト過多
                logger.warning("rate_limit_abort", error=str(e))
                return

            except NotionResourceNotFoundError as e:
                logger.warning("notion_db_not_found", error=str(e))
                return

            except NotionValidationError as e:
                logger.warning("notion_validation_error_skip", error=str(e))
                continue

            except (GitHubAPIError, NotionAPIError, SnowflakeAPIError) as e:
                # それ以外のエラー
                logger.error("api_integration_failed_skip", error=str(e))
                continue

            except Exception as e:
                # 予期せぬエラー
                logger.error("unexpected_error_occurred", error=str(e))


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
