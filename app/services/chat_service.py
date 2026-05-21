"""Chat orchestration service.

This service owns chatbot business logic:
- validates conversation ownership
- saves user and assistant messages
- stores short-term conversation memory in Redis
- routes clear user intents to project tools
- writes explicit long-term memory only when requested
"""

from __future__ import annotations

import inspect
from typing import Any

from app.domain.errors import NotFoundError
from app.infra.redaction import redact_text
from app.repositories.conversation_repo import ConversationRepository
from app.services.memory_service import MemoryService
from app.services.rag_service import RagAnswerRequest, RagService
from app.services.short_term_memory_service import ShortTermMemoryService


class ChatService:
    """Coordinate authenticated chat messages and simple tool execution."""

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        memory_service: MemoryService,
        rag_service: RagService,
        model_client: Any,
        short_term_memory_service: ShortTermMemoryService,
    ) -> None:
        """Store service dependencies."""
        self.conversation_repo = conversation_repo
        self.memory_service = memory_service
        self.rag_service = rag_service
        self.model_client = model_client
        self.short_term_memory_service = short_term_memory_service

    async def handle_message(
        self,
        *,
        user_id: int,
        message: str,
        conversation_id: int | None = None,
    ) -> dict[str, Any]:
        """Handle one authenticated chat message.

        If conversation_id is missing, a new conversation is created.
        If conversation_id is provided, ownership is checked before saving messages.
        """
        redacted_message = redact_text(message)

        if conversation_id is None:
            conversation = await self.conversation_repo.create_conversation(
                user_id=user_id,
                title=self._build_title(redacted_message),
            )
            conversation_id = conversation.id
        else:
            conversation = await self.conversation_repo.get_conversation_by_id(
                conversation_id=conversation_id
            )

            if conversation is None or conversation.user_id != user_id:
                raise NotFoundError("Conversation was not found.")

        user_message = await self.conversation_repo.create_message(
            conversation_id=conversation_id,
            role="user",
            content_redacted=redacted_message,
        )

        await self.short_term_memory_service.append_message(
            conversation_id=conversation_id,
            role="user",
            content=redacted_message,
        )

        assistant_response = await self._route_tool(
            user_id=user_id,
            message=message,
        )

        redacted_assistant_response = redact_text(assistant_response)

        assistant_message = await self.conversation_repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            content_redacted=redacted_assistant_response,
        )

        await self.short_term_memory_service.append_message(
            conversation_id=conversation_id,
            role="assistant",
            content=redacted_assistant_response,
        )

        return {
            "conversation_id": conversation_id,
            "user_message_id": user_message.id,
            "assistant_message_id": assistant_message.id,
            "response": assistant_response,
        }

    async def _route_tool(
        self,
        *,
        user_id: int,
        message: str,
    ) -> str:
        """Route obvious user intent to one project tool.

        This is intentionally deterministic for now. Later, this can be replaced
        by one tool-calling LLM while keeping the same tool methods underneath.
        """
        normalized = message.strip().lower()

        try:
            if self._is_memory_write(normalized):
                memory_text = self._extract_memory_text(message)

                await self.memory_service.write_memory(
                    user_id=user_id,
                    content=memory_text,
                    memory_type="semantic",
                )

                return "Saved this as long-term memory."

            if "classify" in normalized or "label this" in normalized:
                result = await self._call_maybe_async(
                    self.model_client.classify_issue,
                    title="Chat-submitted issue",
                    body=message,
                )

                return self._format_classification(result)

            if self._is_entity_request(normalized):
                result = await self._call_maybe_async(
                    self.model_client.extract_entities,
                    text=message,
                )

                return self._format_entities(result)

            if "summarize" in normalized or "summary" in normalized:
                result = await self._call_maybe_async(
                    self.model_client.summarize_thread,
                    title="Chat-submitted thread",
                    body=message,
                    comments=[],
                )

                return self._format_summary(result)

            if self._looks_like_question(normalized):
                result = await self._call_rag(message)

                return self._format_rag_answer(result)

            return (
                "I can help with classification, entity extraction, summarization, "
                "RAG questions, or explicit memory writes. Try: "
                "'Classify this issue...', 'Extract entities...', 'Summarize...', "
                "'What does the project say about...', or 'Remember that...'"
            )

        except Exception:
            return (
                "One of the chatbot tools is temporarily unavailable, so I could not "
                "complete that tool call right now. The message was still saved."
            )

    async def _call_maybe_async(self, func: Any, **kwargs: Any) -> Any:
        """Call either a sync or async tool function.

        The current model client uses sync module-level HTTP functions.
        This helper keeps ChatService compatible with sync and async adapters.
        """
        result = func(**kwargs)

        if inspect.isawaitable(result):
            return await result

        return result

    async def _call_rag(self, question: str) -> Any:
        """Call the RAG retrieval service using its request model."""
        request = RagAnswerRequest(question=question)
        result = self.rag_service.retrieve_context(request)

        if inspect.isawaitable(result):
            return await result

        return result

    def _is_memory_write(self, normalized: str) -> bool:
        """Detect explicit memory-write requests only."""
        return normalized.startswith("remember that") or normalized.startswith("remember:")

    def _extract_memory_text(self, message: str) -> str:
        """Remove the memory command prefix and keep the actual memory content."""
        stripped = message.strip()

        if stripped.lower().startswith("remember that"):
            return stripped[len("remember that") :].strip(" :")

        if stripped.lower().startswith("remember:"):
            return stripped[len("remember:") :].strip()

        return stripped

    def _is_entity_request(self, normalized: str) -> bool:
        """Detect entity extraction requests without matching words like maintainers."""
        return (
            "extract entities" in normalized
            or "extract entity" in normalized
            or "entity extraction" in normalized
            or normalized.startswith("ner ")
            or normalized == "ner"
        )

    def _looks_like_question(self, normalized: str) -> bool:
        """Detect questions that should go to RAG."""
        question_starters = (
            "what",
            "why",
            "how",
            "when",
            "where",
            "which",
            "can",
            "should",
            "does",
            "do",
            "is",
            "are",
        )

        return normalized.endswith("?") or normalized.startswith(question_starters)

    def _build_title(self, message: str) -> str:
        """Create a short conversation title from the first user message."""
        return message[:60] if message else "New conversation"

    def _format_classification(self, result: Any) -> str:
        """Format classifier output safely for chat."""
        label = self._read_value(result, "label", "unknown")
        confidence = self._read_value(result, "confidence", None)
        model = self._read_value(result, "model", "classifier")

        if confidence is None:
            return f"Classification result: {label} using {model}."

        return f"Classification result: {label} with confidence {confidence} using {model}."

    def _format_entities(self, result: Any) -> str:
        """Format NER output safely for chat."""
        entities = self._read_value(result, "entities", [])

        if not entities:
            return "No code-shaped entities were found."

        return f"Extracted entities: {entities}"

    def _format_summary(self, result: Any) -> str:
        """Format summarizer output safely for chat."""
        summary = self._read_value(result, "summary", None)

        if summary:
            return f"Summary: {summary}"

        return f"Summary result: {result}"

    def _format_rag_answer(self, result: Any) -> str:
        """Format RAG output safely for chat."""
        answer = self._read_value(result, "answer", None)

        if answer:
            return str(answer)

        context = self._read_value(result, "context", None)

        if context:
            return f"Retrieved grounding context:\n{context}"

        chunks = self._read_value(result, "chunks", None)

        if chunks:
            return f"Retrieved {len(chunks)} relevant chunks: {chunks}"

        return str(result)

    def _read_value(self, result: Any, key: str, default: Any) -> Any:
        """Read a value from either a dict or an object."""
        if isinstance(result, dict):
            return result.get(key, default)

        return getattr(result, key, default)