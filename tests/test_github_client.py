import pytest
import respx
import httpx
from http import HTTPStatus

from techtrendwatcher.github.client import GithubClient
from techtrendwatcher.core.exceptions import GitHubAuthError, GitHubRateLimitError, GitHubAPIError

# 成功
@pytest.mark.asyncio
async def test_search_github_success():

    async with httpx.AsyncClient() as client:
        
        github_client = GithubClient(client)

        with respx.mock:
            respx.get("https://api.github.com/search/repositories").mock(
                return_value=httpx.Response(200, json={
                    "total_count": 1,
                    "incomplete_results": False,
                    "items": [
                        {"id": 1, "name": "test-repo", "html_url": "https://...", "stargazers_count": 100, "description": "...", "topics": []}
                    ]
                })
            )

            result = await github_client.search_github("RAG")

            assert result.total_count == 1
            assert result.items[0].id == 1


# 認証のエラー
@pytest.mark.asyncio
async def test_serch_github_fail_auth():

    async with httpx.AsyncClient() as client:    
        # client作成
        github_client = GithubClient(client)

        # mock作成
        with respx.mock:
            respx.get("https://api.github.com/search/repositories").mock(
                return_value=httpx.Response(HTTPStatus.UNAUTHORIZED)
            )

            # 実行して想定通りのエラーが出るかをチェック
            with pytest.raises(GitHubAuthError) as exinfo:
                await github_client.search_github("RAG")
       
            assert "認証エラー" in str(exinfo.value)
            

# Ratelimitエラー
@pytest.mark.asyncio
async def test_search_github_fail_ratelimit(mocker):

    mocker.patch("asyncio.sleep", return_value=None)

    async with httpx.AsyncClient() as client:
        github_client = GithubClient(client)

        with respx.mock:
            route = respx.get("https://api.github.com/search/repositories").mock(
                return_value=httpx.Response(HTTPStatus.FORBIDDEN)
            )

            with pytest.raises(GitHubRateLimitError) as exinfo:
                await github_client.search_github("RAG")

            assert "レート制限" in str(exinfo.value)
            assert route.call_count == 5


# サーバエラー
@pytest.mark.asyncio
async def test_search_github_fail_server_err(mocker):

    mocker.patch("asyncio.sleep", return_value=None)

    # client作成
    async with httpx.AsyncClient() as client:
        github_client = GithubClient(client)

        with respx.mock:
            route = respx.get("https://api.github.com/search/repositories").mock(
                return_value=httpx.Response(HTTPStatus.INTERNAL_SERVER_ERROR)
            )

            with pytest.raises(GitHubAPIError) as exinfo:
                await github_client.search_github("RAG")

            assert "GitHub APIでエラーが発生したわよ" in str(exinfo.value)
            assert route.call_count == 5


# request
@pytest.mark.asyncio
async def test_search_github_fail_request_err(mocker):

    mocker.patch("asyncio.sleep", return_value=None)

    # client作成
    async with httpx.AsyncClient() as client:
        github_client = GithubClient(client)

        with respx.mock:
            route = respx.get("https://api.github.com/search/repositories").mock(
                side_effect=httpx.RequestError("Connection failed")
            )

            with pytest.raises(GitHubAPIError) as exinfo:
                await github_client.search_github("RAG")

            assert "Githubへの接続が失敗" in str(exinfo.value)
            assert route.call_count == 5