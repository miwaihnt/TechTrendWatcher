import asyncio

import polars as pl
from snowflake.snowpark import Session

from techtrendwatcher.core.config import SnowflakeConfig
from techtrendwatcher.core.logger import get_logger


class Client:
    def __init__(self, account_parameter: SnowflakeConfig):
        self.logger = get_logger(__name__)
        self.settings = account_parameter
        self.session = Session.builder.configs(
            account_parameter.model_dump(by_alias=True)
        ).create()
        self.table_name = self.settings.table

    async def upload_to_snowflake(self, df: pl.DataFrame) -> None:

        # すべてのカラム名を大文字に変換する（Snowflake のお作法）
        df = df.rename({col: col.upper() for col in df.columns})

        # DataFrameをdictに変換
        pandas_df = df.to_pandas()

        # 書き込み
        await asyncio.to_thread(
            self.session.write_pandas,
            pandas_df,
            table_name=self.table_name,
            auto_create_table=True,
        )
