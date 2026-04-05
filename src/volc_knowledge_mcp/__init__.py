import json
import os
import requests
from typing import Optional

from volcengine.auth.SignerV4 import SignerV4
from volcengine.base.Request import Request
from volcengine.Credentials import Credentials
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("VolcengineKnowledgeSearch", description="火山方舟知识库检索工具，可查询您的私有知识库中的内容")

AK = os.getenv("VOLC_AK")
SK = os.getenv("VOLC_SK")
ACCOUNT_ID = os.getenv("VOLC_ACCOUNT_ID")
COLLECTION_NAME = os.getenv("VOLC_COLLECTION_NAME", "urban_plan")
PROJECT_NAME = os.getenv("VOLC_PROJECT_NAME", "default")
KNOWLEDGE_BASE_DOMAIN = os.getenv("VOLC_KNOWLEDGE_DOMAIN", "api-knowledgebase.mlp.cn-beijing.volces.com")


def prepare_request(method, path, params=None, data=None, doseq=0):
    if params:
        for key in params:
            if (
                    isinstance(params[key], int)
                    or isinstance(params[key], float)
                    or isinstance(params[key], bool)
            ):
                params[key] = str(params[key])
            elif isinstance(params[key], list):
                if not doseq:
                    params[key] = ",".join(params[key])
    r = Request()
    r.set_shema("http")
    r.set_method(method)
    r.set_connection_timeout(10)
    r.set_socket_timeout(10)
    mheaders = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "Host": KNOWLEDGE_BASE_DOMAIN,
        "V-Account-Id": ACCOUNT_ID,
    }
    r.set_headers(mheaders)
    if params:
        r.set_query(params)
    r.set_host(KNOWLEDGE_BASE_DOMAIN)
    r.set_path(path)
    if data is not None:
        r.set_body(json.dumps(data))

    credentials = Credentials(AK, SK, "air", "cn-north-1")
    SignerV4.sign(r, credentials)
    return r


@mcp.tool()
def search_knowledge(query: str, limit: Optional[int] = 5) -> str:
    """
    在火山方舟的私有知识库中检索相关知识，用于回答用户的问题，获取知识库中的文档、资料内容。
    
    Args:
        query: 用户的问题或要检索的关键词，例如"DLSP论文是关于什么的"
        limit: 最多返回的检索结果数量，默认5条
    """
    if not AK or not SK or not ACCOUNT_ID:
        return "错误：未配置火山方舟的AK/SK/AccountID，请检查环境变量配置。"

    method = "POST"
    path = "/api/knowledge/collection/search_knowledge"
    request_params = {
        "project": PROJECT_NAME,
        "name": COLLECTION_NAME,
        "query": query,
        "limit": limit,
        "pre_processing": {
            "need_instruction": True,
            "return_token_usage": True,
            "messages": [
                {
                    "role": "system",
                    "content": ""
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
        },
        "dense_weight": 0.5,
        "post_processing": {
            "get_attachment_link": True,
            "rerank_only_chunk": False,
            "rerank_switch": False
        }
    }

    try:
        info_req = prepare_request(method=method, path=path, data=request_params)
        rsp = requests.request(
            method=info_req.method,
            url=f"http://{KNOWLEDGE_BASE_DOMAIN}{info_req.path}",
            headers=info_req.headers,
            data=info_req.body
        )
        
        if rsp.status_code != 200:
            return f"检索失败，API返回错误：{rsp.status_code} {rsp.text}"
        
        result = rsp.json()
        if result.get("code") != 0:
            return f"检索失败：{result.get('msg', '未知错误')}"
        
        knowledge_list = result.get("data", {}).get("search_result", [])
        if not knowledge_list:
            return "未检索到相关知识。"
        
        response = f"已为您在火山知识库中检索到{len(knowledge_list)}条相关内容：\n\n"
        for i, item in enumerate(knowledge_list, 1):
            response += f"--- 结果{i} ---\n"
            response += f"文档名称：{item.get('doc_name', '未知文档')}\n"
            response += f"相关度：{item.get('score', 0):.2f}\n"
            response += f"内容：{item.get('content', '无内容')}\n"
            if item.get("attachment_link"):
                response += f"文档链接：{item.get('attachment_link')}\n"
            response += "\n"
        
        return response
        
    except Exception as e:
        return f"检索过程发生错误：{str(e)}"


def main():
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()
