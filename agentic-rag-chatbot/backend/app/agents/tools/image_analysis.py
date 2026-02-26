"""画像解析ツール

OpenAI GPT-4o Vision APIを使用して画像を解析し、
エラーコード、UI要素、テキストを抽出する。
"""

import re
from typing import Any

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from app.agents.llm_factory import get_llm


VISION_PROMPT = """この画像を解析して、以下の情報を抽出してください。

1. **エラーコード**: 画像内に表示されているエラーコード（例: E001, ERR-123, 404など）
2. **UI要素**: 表示されているボタン、入力欄、アイコンなどのUI要素
3. **テキスト**: 画像内の主要なテキスト内容
4. **概要**: 画像の内容を簡潔に説明

以下の形式で回答してください:
- エラーコード: [コード1, コード2, ...]
- UI要素: [要素1, 要素2, ...]
- テキスト: "画像内のテキスト"
- 概要: "画像の説明"
"""


def _parse_analysis_response(content: str) -> dict[str, Any]:
    """解析レスポンスをパースして構造化データを返す"""
    result = {
        "error_codes": [],
        "ui_elements": [],
        "extracted_text": "",
        "summary": "",
    }
    
    # エラーコードを抽出
    error_match = re.search(r"エラーコード[：:]\s*\[([^\]]*)\]", content)
    if error_match:
        codes_str = error_match.group(1)
        codes = [c.strip().strip("'\"") for c in codes_str.split(",") if c.strip()]
        result["error_codes"] = codes
    
    # UI要素を抽出
    ui_match = re.search(r"UI要素[：:]\s*\[([^\]]*)\]", content)
    if ui_match:
        elements_str = ui_match.group(1)
        elements = [e.strip().strip("'\"") for e in elements_str.split(",") if e.strip()]
        result["ui_elements"] = elements
    
    # テキストを抽出
    text_match = re.search(r"テキスト[：:]\s*[\"']([^\"']*)[\"']", content)
    if text_match:
        result["extracted_text"] = text_match.group(1)
    
    # 概要を抽出
    summary_match = re.search(r"概要[：:]\s*[\"']([^\"']*)[\"']", content)
    if summary_match:
        result["summary"] = summary_match.group(1)
    
    return result


@tool
def analyze_image(image_data: str) -> dict[str, Any]:
    """画像を解析してエラーコード、UI要素、テキストを抽出します。

    Args:
        image_data: Base64エンコードされた画像データ

    Returns:
        解析結果を含む辞書:
        - error_codes: 検出されたエラーコードのリスト
        - ui_elements: 検出されたUI要素のリスト
        - extracted_text: 画像から抽出されたテキスト
        - summary: 画像の概要説明
    """
    if not image_data:
        return {
            "error_codes": [],
            "ui_elements": [],
            "extracted_text": "",
            "summary": "",
        }
    
    try:
        # Vision APIを使用するためにGPT-4oモデルを取得
        llm = get_llm(temperature=0.0)
        
        # 画像を含むメッセージを作成
        message = HumanMessage(
            content=[
                {"type": "text", "text": VISION_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_data}",
                    },
                },
            ]
        )
        
        # LLMを呼び出して解析
        response = llm.invoke([message])
        
        # レスポンスをパース
        return _parse_analysis_response(response.content)
    
    except Exception as e:
        return {
            "error_codes": [],
            "ui_elements": [],
            "extracted_text": "",
            "summary": f"画像解析エラー: {str(e)}",
        }
