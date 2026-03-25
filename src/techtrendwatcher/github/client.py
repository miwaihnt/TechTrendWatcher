from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from techtrendwatcher.core.config import get_settings
from techtrendwatcher.core.logger import get_logger
from techtrendwatcher.models.github import GithubAPIFull


class GithubClient:
    def __init__(self, client: httpx.AsyncClient):
        self.setting = get_settings()
        self.logger = get_logger(__name__)
        self.client = client

    # 検索
    @retry(
        # 待ち時間を4秒から開始、最大60秒まで
        wait=wait_exponential(multiplier=1, min=4, max=60),
        # 最大リトライ５回
        stop=stop_after_attempt(5),
        # httpx.HttpStatusError (4xx,5xx)が発生した時にリトライ対象
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        # 最終的に失敗した時に元の例外を投げる
        reraise=True,
    )
    async def search_github(self, query: str) -> GithubAPIFull:
        url = "https://api.github.com/search/repositories"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.setting.github_token}",
            "X-Github-Api-Version": "2022-11-28",
        }

        params: dict[str, Any] = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 5,
        }

        try:
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            response_json = response.json()
            full_result = GithubAPIFull.model_validate(response_json)
            return full_result

        except Exception as e:
            print(f"エラーが発生しました:{e}")
            raise e
