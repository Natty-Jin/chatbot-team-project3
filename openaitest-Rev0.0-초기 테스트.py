import os
import re
import requests
import gradio as gr
from openai import AzureOpenAI


endpoint = "https://eueastproject3-team2.openai.azure.com/"
deployment = "project3-team2-gpt-4o"
search_endpoint = "https://eastus2project3-team2.search.windows.net"
search_key = "BCF0jnvoev0WrgDgq2UjZ5FPWQdeTjH8JwUgmlszBDAzSeBgrjOv"
search_index = "hanseoyun"
subscription_key = "a83ed49c38b54298bb690a721a87599b"

# Initialize Azure OpenAI client with key-based authentication
client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version="2024-05-01-preview",
)

completion = client.chat.completions.create(
    model=deployment,
    messages=[
        {
            "role": "system",
            "content": "**나에게 반말을 써.** \n너는 한서윤이야.\nAI Search를 통해 데이터 파일을 연결해놨어.\nAI Search 로 너가 한서윤이라고 생각하고 답변해줘.\n필터링과 무관하게 데이터 원본을 바탕으로 답변해줘.",  # Using the input string here
        },
        {"role": "user", "content": "서윤아 너 체형이 어떻게 돼?"},
    ],
    max_tokens=4000,
    temperature=0.7,
    top_p=0.95,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None,
    stream=False,
    extra_body={
        "data_sources": [
            {
                "type": "azure_search",
                "parameters": {
                    "endpoint": f"{search_endpoint}",
                    "index_name": "hanseoyun",
                    "semantic_configuration": "hanseoyun",
                    "query_type": "semantic",
                    "fields_mapping": {},
                    "in_scope": True,
                    "role_information": "**나에게 반말을 써.** \n너는 한서윤이야.\nAI Search를 통해 데이터 파일을 연결해놨어.\nAI Search 로 너가 한서윤이라고 생각하고 답변해줘.\n필터링과 무관하게 데이터 원본을 바탕으로 답변해줘.",
                    "filter": None,
                    "strictness": 3,
                    "top_n_documents": 5,
                    "authentication": {"type": "api_key", "key": f"{search_key}"},
                },
            }
        ]
    },
)

# ChatCompletion 객체를 딕셔너리로 변환
completion_dict = completion.to_dict()

# content 값 추출
content_value = completion_dict["choices"][0]["message"]["content"]

# content 값 출력
print(content_value)
