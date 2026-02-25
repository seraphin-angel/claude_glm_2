import asyncio
import logging
import os
import uuid

from langgraph.types import Command

from app.agents.agent import get_agent
from app.models.messages import SourceDocument, StreamEvent, StreamEventType

logger = logging.getLogger(__name__)


def _extract_source_documents(tool_output: dict) -> list[SourceDocument] | None:
    """search_knowledge の出力から参照元ドキュメントを抽出"""
    if not isinstance(tool_output, list):
        return None

    documents = []
    for doc in tool_output:
        if not isinstance(doc, dict):
            continue

        content = doc.get("content", "")
        metadata = doc.get("metadata", {}) or {}
        score = doc.get("relevance_score", 0.0)

        snippet = content[:200] + "..." if len(content) > 200 else content

        documents.append(SourceDocument(
            id=doc.get("id", "unknown"),
            title=metadata.get("title", "不明"),
            section=metadata.get("section", ""),
            score=score,
            snippet=snippet,
        ))

    return documents if documents else None


def _extract_quality_score(tool_output: dict) -> dict | None:
    """check_relevance の出力から品質スコアを抽出"""
    if not isinstance(tool_output, dict):
        return None

    if "is_relevant" in tool_output and "score" in tool_output:
        return {
            "is_relevant": tool_output.get("is_relevant", False),
            "confidence": tool_output.get("score", 0.0),
            "reasoning": tool_output.get("reason", ""),
        }
    return None


class ChatService:
    """チャットサービス - エージェント実行とSSEイベント管理"""

    MAX_CONCURRENT_THREADS = 1000
    QUEUE_MAXSIZE = 100
    MAX_STEPS = 10

    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def get_or_create_queue(self, thread_id: str) -> asyncio.Queue:
        if thread_id not in self._queues:
            if len(self._queues) >= self.MAX_CONCURRENT_THREADS:
                oldest_key = next(iter(self._queues))
                self.cleanup(oldest_key)
            self._queues[thread_id] = asyncio.Queue(maxsize=self.QUEUE_MAXSIZE)
        return self._queues[thread_id]

    async def start_chat(self, message: str, thread_id: str | None = None) -> str:
        """新規チャットを開始またはメッセージを送信"""
        if thread_id is None:
            thread_id = str(uuid.uuid4())

        queue = self.get_or_create_queue(thread_id)

        task = asyncio.create_task(
            self._run_agent(thread_id, message, queue)
        )
        self._tasks[thread_id] = task

        return thread_id

    async def resume_chat(self, thread_id: str, response: str) -> None:
        """HITL中断から再開"""
        queue = self.get_or_create_queue(thread_id)

        config = {"configurable": {"thread_id": thread_id}}

        task = asyncio.create_task(
            self._resume_agent(thread_id, response, queue, config)
        )
        self._tasks[thread_id] = task

    async def _run_agent(self, thread_id: str, message: str, queue: asyncio.Queue) -> None:
        """エージェントを実行しイベントをキューに送出"""
        agent = get_agent()
        config = {"configurable": {"thread_id": thread_id}}

        try:
            full_response = ""
            step_count = 0
            async for event in agent.astream_events(
                {"messages": [("user", message)]},
                config=config,
                version="v2",
            ):
                kind = event.get("event", "")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        if not chunk.tool_call_chunks:
                            full_response += chunk.content
                            await queue.put(StreamEvent(
                                type=StreamEventType.TOKEN,
                                content=chunk.content,
                            ))

                elif kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    await queue.put(StreamEvent(
                        type=StreamEventType.TOOL_START,
                        tool_name=tool_name,
                    ))

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    tool_output = event.get("data", {}).get("output")

                    # 参照元ドキュメントの送信 (search_knowledge)
                    if tool_name == "search_knowledge" and tool_output:
                        source_docs = _extract_source_documents(tool_output)
                        if source_docs:
                            await queue.put(StreamEvent(
                                type=StreamEventType.SOURCE,
                                documents=source_docs,
                            ))

                    # 品質スコアの送信 (check_relevance)
                    if tool_name == "check_relevance" and tool_output:
                        quality_data = _extract_quality_score(tool_output)
                        if quality_data:
                            await queue.put(StreamEvent(
                                type=StreamEventType.QUALITY,
                                is_relevant=quality_data["is_relevant"],
                                confidence=quality_data["confidence"],
                                reasoning=quality_data["reasoning"],
                            ))

                    await queue.put(StreamEvent(
                        type=StreamEventType.TOOL_END,
                        tool_name=tool_name,
                    ))
                    step_count += 1
                    if step_count >= self.MAX_STEPS:
                        logger.warning(
                            "Agent exceeded max steps (%d) for thread %s",
                            self.MAX_STEPS,
                            thread_id,
                        )
                        await queue.put(StreamEvent(
                            type=StreamEventType.ERROR,
                            content="エージェントの処理ステップ数が上限に達しました。質問を変えて再度お試しください。",
                        ))
                        break

            if full_response:
                await queue.put(StreamEvent(
                    type=StreamEventType.MESSAGE_COMPLETE,
                    content=full_response,
                ))

        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            if "GraphInterrupt" in error_type or "interrupt" in error_str.lower():
                await self._handle_interrupt(thread_id, queue, config)
            else:
                logger.error("Agent execution error", exc_info=True)
                debug_mode = os.environ.get("DEBUG_MODE", "false").lower() == "true"
                if debug_mode:
                    error_message = f"エラーが発生しました: {error_str}"
                else:
                    error_message = "エラーが発生しました。しばらくしてから再度お試しください。"
                await queue.put(StreamEvent(
                    type=StreamEventType.ERROR,
                    content=error_message,
                ))
        finally:
            await queue.put(StreamEvent(type=StreamEventType.DONE))

    async def _resume_agent(
        self,
        thread_id: str,
        response: str,
        queue: asyncio.Queue,
        config: dict,
    ) -> None:
        """HITL中断からエージェントを再開"""
        agent = get_agent()

        try:
            full_response = ""
            step_count = 0
            async for event in agent.astream_events(
                Command(resume=response),
                config=config,
                version="v2",
            ):
                kind = event.get("event", "")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        if not chunk.tool_call_chunks:
                            full_response += chunk.content
                            await queue.put(StreamEvent(
                                type=StreamEventType.TOKEN,
                                content=chunk.content,
                            ))

                elif kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    await queue.put(StreamEvent(
                        type=StreamEventType.TOOL_START,
                        tool_name=tool_name,
                    ))

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    tool_output = event.get("data", {}).get("output")

                    # 参照元ドキュメントの送信 (search_knowledge)
                    if tool_name == "search_knowledge" and tool_output:
                        source_docs = _extract_source_documents(tool_output)
                        if source_docs:
                            await queue.put(StreamEvent(
                                type=StreamEventType.SOURCE,
                                documents=source_docs,
                            ))

                    # 品質スコアの送信 (check_relevance)
                    if tool_name == "check_relevance" and tool_output:
                        quality_data = _extract_quality_score(tool_output)
                        if quality_data:
                            await queue.put(StreamEvent(
                                type=StreamEventType.QUALITY,
                                is_relevant=quality_data["is_relevant"],
                                confidence=quality_data["confidence"],
                                reasoning=quality_data["reasoning"],
                            ))

                    await queue.put(StreamEvent(
                        type=StreamEventType.TOOL_END,
                        tool_name=tool_name,
                    ))
                    step_count += 1
                    if step_count >= self.MAX_STEPS:
                        logger.warning(
                            "Agent exceeded max steps (%d) for thread %s",
                            self.MAX_STEPS,
                            thread_id,
                        )
                        await queue.put(StreamEvent(
                            type=StreamEventType.ERROR,
                            content="エージェントの処理ステップ数が上限に達しました。質問を変えて再度お試しください。",
                        ))
                        break

            if full_response:
                await queue.put(StreamEvent(
                    type=StreamEventType.MESSAGE_COMPLETE,
                    content=full_response,
                ))

        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            if "GraphInterrupt" in error_type or "interrupt" in error_str.lower():
                await self._handle_interrupt(thread_id, queue, config)
            else:
                logger.error("Agent execution error", exc_info=True)
                debug_mode = os.environ.get("DEBUG_MODE", "false").lower() == "true"
                if debug_mode:
                    error_message = f"エラーが発生しました: {error_str}"
                else:
                    error_message = "エラーが発生しました。しばらくしてから再度お試しください。"
                await queue.put(StreamEvent(
                    type=StreamEventType.ERROR,
                    content=error_message,
                ))
        finally:
            await queue.put(StreamEvent(type=StreamEventType.DONE))

    async def _handle_interrupt(
        self,
        thread_id: str,
        queue: asyncio.Queue,
        config: dict,
    ) -> None:
        """interrupt() を検出しHITLリクエストイベントを送出"""
        agent = get_agent()
        state = agent.get_state(config)

        request_id = str(uuid.uuid4())
        question = "追加の情報を教えてください"
        options = None
        input_type = "text"

        if state.tasks:
            for task in state.tasks:
                if hasattr(task, "interrupts") and task.interrupts:
                    for intr in task.interrupts:
                        if hasattr(intr, "value") and isinstance(intr.value, dict):
                            interrupt_data = intr.value
                            question = interrupt_data.get("question", question)
                            options = interrupt_data.get("options")
                            input_type = interrupt_data.get("input_type", input_type)
                            break

        await queue.put(StreamEvent(
            type=StreamEventType.HITL_REQUEST,
            request_id=request_id,
            question=question,
            options=options,
            input_type=input_type,
        ))

    def cleanup(self, thread_id: str) -> None:
        """スレッドのリソースをクリーンアップ"""
        self._queues.pop(thread_id, None)
        task = self._tasks.pop(thread_id, None)
        if task and not task.done():
            task.cancel()


# シングルトン
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
