from http import HTTPStatus
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from techtrendwatcher.core.config import get_settings
from techtrendwatcher.core.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubRateLimitError,
    GitHubValidationError,
)
from techtrendwatcher.core.logger import get_logger
from techtrendwatcher.models.github import GithubAPIFull

# リトライ設定の定数化
GITHUB_RETRY_MULTIPLIER = 1
GITHUB_RETRY_MIN_WAIT = 4
GITHUB_RETRY_MAX_WAIT = 60
GITHUB_RETRY_MAX_ATTEMPTS = 5


# retry条件を決める
def is_retryable_error(exception: Exception) -> bool:
    # timeout
    if isinstance(exception, httpx.RequestError):
        return True
    # レート制限
    if isinstance(exception, GitHubRateLimitError):
        return True

    if isinstance(exception, GitHubAPIError):
        if getattr(exception, "original_error", None) and isinstance(
            exception.original_error, httpx.RequestError
        ):
            return True
        if exception.status_code in [500, 502, 503, 504]:
            return True

    return False


def retry_log(retry_state):
    logger = get_logger(__name__)
    logger.warning(
        "GitHub APIのリトライ中。。。",
        retry_cnt = retry_state.attempt_number,
        retry_reason = retry_state.outcome.exception()
    )


class GithubClient:
    def __init__(self, client: httpx.AsyncClient):
        self.setting = get_settings()
        self.logger = get_logger(__name__)
        self.client = client

    # 検索
    @retry(
        # 待ち時間を4秒から開始、最大60秒まで
        wait=wait_exponential(
            multiplier=GITHUB_RETRY_MULTIPLIER,
            min=GITHUB_RETRY_MIN_WAIT,
            max=GITHUB_RETRY_MAX_WAIT,
        ),
        # 最大リトライ５回
        stop=stop_after_attempt(GITHUB_RETRY_MAX_ATTEMPTS),
        # httpx.HttpStatusError (4xx,5xx)が発生した時にリトライ対象
        retry=retry_if_exception(is_retryable_error),
        # before
        before_sleep=retry_log,
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

        except httpx.HTTPStatusError as e:
            # Httpエラー
            status_code = e.response.status_code

            if status_code == HTTPStatus.UNAUTHORIZED:
                raise GitHubAuthError(
                    "Github認証エラーが発生しました。認証トークンを確認してください",
                    status_code=status_code,
                    original_error=e,
                ) from e

            if status_code in (HTTPStatus.FORBIDDEN, HTTPStatus.TOO_MANY_REQUESTS):
                raise GitHubRateLimitError(
                    "レート制限よ！少し頭を冷やしなさい！",
                    status_code=status_code,
                    original_error=e,
                ) from e

            if status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
                raise GitHubValidationError(
                    "クエリがデタラメよ！", status_code=status_code, original_error=e
                ) from e

            raise GitHubAPIError(
                f"GitHub APIでエラーが発生したわよ: {e}",
                status_code=status_code,
                original_error=e,
            ) from e

        except httpx.RequestError as e:
            # タイムアウトを捕まえる
            raise GitHubAPIError(f"Githubへの接続が失敗:{e}", original_error=e) from e

        except Exception as e:
            raise GitHubAPIError("予期せぬエラーが発生したわ", original_error=e) from e
