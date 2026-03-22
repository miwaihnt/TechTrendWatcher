from techtrendwatcher.github.client import GithubClient
from techtrendwatcher.github.processor import convert_to_dataframe, save_as_parquet, get_trend_dataframe, convert_to_silver_dataframe
from techtrendwatcher.core.logger import setup_logging,get_logger
from techtrendwatcher.core.config import get_settings
from techtrendwatcher.core.exceptions import ConfigurationError
from techtrendwatcher.notion.client import NotionClient
from techtrendwatcher.snowflake.client import Client
import httpx
import asyncio

async def main():

    # logingの初期設定
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Stargint techtrendwatcher")

    # 各種.envの設定
    try:
        settings = get_settings()
    except ConfigurationError as e:
        # error概要
        logger.error(f"起動時の設定ファイルエラー:{e}")

        # error詳細
        if e.original_error:
            logger.error(f"詳細な原因：{e.original_error}")
        return

    # httpクライアントの作成
    async with httpx.AsyncClient() as shared_client:

        """
        Githubの検索〜加工
        """

        # github clientの作成
        client = GithubClient(shared_client)
        for query in settings.serch_query:
            try:
                """
                ここから一連の処理
                1. Githubからの取得
                2. 加工と保存
                3. Notionの更新
                4. Snowflakeのロード
                """
                logger.info(f"processing serch query:{query}")
                result = await client.search_github(query)

                # notiony用のgithub api responseをpolarsで処理
                co_git_api_res = convert_to_dataframe(result)

                # snowflake用のgithub api responseをpolarsで処理
                snowflake_git_serch_to_pl = convert_to_silver_dataframe(result,query)
                logger.info(f"snowflake_git_serch_to_pl:{snowflake_git_serch_to_pl}")
                # githubのレスポンスをparquetで保存
                save_as_parquet(co_git_api_res,query)

                # 過去のレスポンスと比較し、スターに変更のあるものだけを検知
                trend_df = get_trend_dataframe(co_git_api_res,query)

                """
                Notionへの挿入
                """
                # Notionへの書き込み
                notion_client = NotionClient(shared_client)

                # セマフォの設定
                semaphore = asyncio.Semaphore(settings.notion_semaphore)

                async def limited_upsert(row):
                    async with semaphore:
                        return await notion_client.upsert_repo(row)

                # Notionにすでにレコードがあるかチェックし、upsertを行う(並列実行)
                tasks = [limited_upsert(row) for row in trend_df.to_dicts()]
                await asyncio.gather(*tasks)

                """
                snowflakefへの書き込み
                """
                snowflake_client = Client(settings.snowflake)
                writer_result = await snowflake_client.upload_to_snowflake(snowflake_git_serch_to_pl)
                logger.info(f"snowflake write:{writer_result}")

                logger.info(f"Success:{query}")

            except Exception as e:
                logger.error(f"Failed to process {query}, Error:{e}")
    
if __name__ == "__main__":
    asyncio.run(main())
