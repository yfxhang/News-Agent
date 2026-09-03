import os
import json
from openai import OpenAI


client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com"
)


def analyze_news(article):

    prompt = f"""
你是一名专业的中国金属产业研究员。

请分析下面这条新闻：

标题：
{article["title"]}

摘要：
{article["summary"]}

发布时间：
{article["published"]}

请判断：

1. 新闻重要性，1-5分
2. 新闻类别
3. 涉及的金属
4. 对产业链的影响
5. 对价格的潜在影响
6. 用一句话总结
7. 是否值得进入每日新闻简报

只返回 JSON，不要返回 Markdown，不要添加其他文字。

JSON格式：

{{
    "importance": 1,
    "category": "",
    "metals": [],
    "industry_impact": "",
    "price_impact": "",
    "summary": "",
    "push": false
}}
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    text = response.choices[0].message.content

    return json.loads(text)
