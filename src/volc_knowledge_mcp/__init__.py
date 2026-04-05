import json
import os
import requests
from typing import Optional, Union, List, Dict

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("VolcengineKnowledgeSearch")

API_KEY = os.getenv("VOLC_API_KEY")
ACCOUNT_ID = os.getenv("VOLC_ACCOUNT_ID")
SERVICE_RESOURCE_ID = os.getenv("VOLC_SERVICE_RESOURCE_ID")
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
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json;charset=UTF-8",
        "Host": KNOWLEDGE_BASE_DOMAIN,
        "Authorization": f"Bearer {API_KEY}"
    }
    return {
        "method": method,
        "path": path,
        "headers": headers,
        "body": json.dumps(data) if data else None
    }


@mcp.tool()
def search_knowledge(query: str, limit: Optional[int] = 5) -> str:
    """
    在火山方舟的私有知识库中检索相关知识，用于回答用户的问题，获取知识库中的文档、资料内容。
    
    Args:
        query: 用户的问题或要检索的关键词，例如"DLSP论文是关于什么的"
        limit: 最多返回的检索结果数量，默认5条
    """
    if not API_KEY:
        return "错误：未配置火山方舟的API密钥(VOLC_API_KEY)"
    if not SERVICE_RESOURCE_ID:
        return "错误：未配置知识库服务资源ID(VOLC_SERVICE_RESOURCE_ID)"

    method = "POST"
    path = "/api/knowledge/service/chat"
    request_params = {
        "service_resource_id": SERVICE_RESOURCE_ID,
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "stream": False
    }

    try:
        info_req = prepare_request(method=method, path=path, data=request_params)
        rsp = requests.request(
            method=info_req["method"],
            url=f"http://{KNOWLEDGE_BASE_DOMAIN}{info_req['path']}",
            headers=info_req["headers"],
            data=info_req["body"],
            timeout=60
        )
        
        rsp.encoding = "utf-8"
        
        if rsp.status_code != 200:
            return f"检索失败，API返回错误：HTTP {rsp.status_code}\n响应内容：{rsp.text[:500]}"
        
        result = rsp.json()
        
        if result.get("code") and result.get("code") != 0:
            return f"检索失败：{result.get('message', '未知错误')}\n完整响应：{json.dumps(result, ensure_ascii=False)[:500]}"
        
        response_text = result.get("data", {}).get("content", "")
        if not response_text:
            response_text = result.get("result", "")
        if not response_text:
            response_text = json.dumps(result, ensure_ascii=False, indent=2)
        
        return f"知识库检索结果：\n\n{response_text}"
        
    except requests.exceptions.Timeout:
        return "错误：请求超时，请检查网络连接或稍后重试。"
    except requests.exceptions.ConnectionError as e:
        return f"错误：网络连接失败，{str(e)}"
    except json.JSONDecodeError:
        return f"错误：API返回非JSON格式，响应内容：{rsp.text[:200] if 'rsp' in dir() else '无响应'}"
    except Exception as e:
        return f"检索过程发生错误：{type(e).__name__}: {str(e)}"


def main():
    mcp.run(transport='stdio')


__all__ = ["main", "mcp", "search_knowledge"]

if __name__ == "__main__":
    main()
