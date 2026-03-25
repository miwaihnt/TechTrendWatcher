from datetime import datetime
from pathlib import Path

import polars as pl

from techtrendwatcher.core.logger import get_logger
from techtrendwatcher.models.github import GithubAPIFull

"""
apiから取得したgithubリポジトリの情報を
snowflakeに流し込むためにdataframeに変換しpolarsで操作する
"""


def convert_to_silver_dataframe(github_resp: GithubAPIFull, query: str) -> pl.DataFrame:
    items_as_dict = [item.model_dump() for item in github_resp.items]
    df = pl.DataFrame(items_as_dict)
    df = df.with_columns(
        search_query=pl.lit(query),
        captured_at=pl.lit(datetime.now()),
        raw_data=pl.Series(items_as_dict, dtype=pl.Object),
    )
    return df.select(["id", "name", "stargazers_count", "search_query", "raw_data"])


"""
apiから取得したgithubリポジトリの情報を
notionに流し込むためにdataframeに変換しpolarsで操作する
"""


def convert_to_dataframe(github_resp: GithubAPIFull) -> pl.DataFrame:

    # pydanticのリストをdictのリストに変換する
    data = [resp.model_dump() for resp in github_resp.items]
    # polarsのdataframeに変換
    df = pl.DataFrame(data)
    df = df.with_columns(captured_at=pl.lit(datetime.now()))

    return df


"""
convert_to_dataで整理したデータをParquetでローカルに保存（差分抽出用）
"""


def save_as_parquet(df: pl.DataFrame, query: str) -> None:
    logger = get_logger(__name__)

    project_path = Path(__file__).parent.parent
    safe_query = query.replace(" ", "_").lower()
    save_dir = project_path / "data" / "raw" / safe_query
    save_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = save_dir / f"github_repos_{timestamp}.parquet"

    df.write_parquet(save_path)
    logger.info(f"DataFrameを保存しました：{save_path} 行数:{len(df)}")


"""
前回、今回取得したリポジトリ情報を比較（local parquet）し
スターの増加がある場合のみNotionの連携対象とする。
"""

compare_file_num = 2


def get_trend_dataframe(current_df: pl.DataFrame, query: str) -> pl.DataFrame:
    logger = get_logger(__name__)

    # parquetの格納ディレクトリの設定
    project_path = Path(__file__).parent.parent
    safe_query = query.replace(" ", "_").lower()
    file_dir = project_path / "data" / "raw" / safe_query

    # 時系列順にソートし、2番目に新しいものを取得（1番目新しいものは先ほど生成したもの）
    sorted_files = sorted(file_dir.glob("*.parquet"))
    if len(sorted_files) >= compare_file_num:
        prev_file = sorted_files[-2]
        logger.info(f"前回ファイルの取得！sorted_files:{sorted_files[-2]}")
        # 取得した過去ファイルをpolarsで読み込む
        prev_df = pl.read_parquet(prev_file)

        # 取得した最新ファイルと過去ファイルを比較。
        join_df = current_df.join(prev_df, on="id", how="left", suffix="_prev")

        trend_df = join_df.with_columns(
            star_delta=(
                pl.col("stargazers_count")
                - pl.col("stargazers_count_prev").fill_null(0)
            )
        ).filter(pl.col("star_delta") > 0)

        logger.info(f"trend_df:{trend_df}")
        return trend_df

    else:
        logger.warning("過去に処理したparquetファイルが見つかりません")
        return current_df.with_columns(star_delta=pl.col("stargazers_count"))
