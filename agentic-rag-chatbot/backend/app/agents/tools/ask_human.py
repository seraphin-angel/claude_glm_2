from langchain_core.tools import tool
from langgraph.types import interrupt


@tool
def ask_human(question: str, options: list[str] | None = None, input_type: str = "text") -> str:
    """ユーザーに追加情報を確認するために質問します。

    分類や回答生成の過程で追加情報が必要な場合に使用します。

    Args:
        question: ユーザーに対する質問文
        options: 選択肢のリスト（ボタン表示用、Noneの場合はフリーテキスト）
        input_type: 入力タイプ ("buttons" または "text")

    Returns:
        ユーザーからの回答
    """
    if options and input_type != "text":
        input_type = "buttons"
    elif not options:
        input_type = "text"

    response = interrupt({
        "question": question,
        "options": options,
        "input_type": input_type,
    })

    return response
