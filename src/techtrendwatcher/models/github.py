from pydantic import BaseModel, ConfigDict, model_validator
from typing import List, Any
from datetime import datetime



"""GithubAPIのItems内の各要素"""
class GithubAPIItem(BaseModel):
    id:int
    name:str
    html_url:str
    stargazers_count:int
    description:str
    language:str | None = None
    topics:List[str]  

"""Notionに蓄積する必要なものだけを集めたclass"""
class GithubAPISummary(BaseModel):
    total_count:int
    items:List[GithubAPIItem] = []


"""Githubから取得する全量を保持"""
class GithubAPIFull(BaseModel):
    model_config = ConfigDict(extra="allow")
    total_count:int
    incomplete_results:bool
    items:List[GithubAPIItem] | None = []
    row_data:dict | None = None

    @model_validator(mode='before')
    @classmethod
    def capture_raw_data(cls, data:Any) -> Any:
        if isinstance(data,dict):
            data['row_data'] = data
        return data

"""SnowflakeといったWHのRaw層に蓄積するclass"""
class GithubSilverRecord(BaseModel):
    id:int
    name:str
    stargazers_count: int
    search_query: str
    captured_at: datetime
    raw_data:dict

