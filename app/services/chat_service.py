"""Chat orchestration service.

This service owns chatbot business logic:
- validates conversation ownership
- saves user and assistant messages
- stores short-term conversation memory in Redis
- routes clear user intents to project tools
- writes explicit long-term memory only when requested
- formats tool outputs into maintainer-friendly chatbot responses
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

                return self._format_memory_write(memory_text)

            if self._is_memory_lookup(normalized):
                memories = await self.memory_service.list_user_memories(
                    user_id=user_id,
                    limit=5,
                )

                return self._format_memory_recall(memories)

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
                "I can help you triage maintainer work.\n\n"
                "Try one of these:\n"
                "- `Classify this issue: ...`\n"
                "- `Extract entities from this issue: ...`\n"
                "- `Summarize this thread: ...`\n"
                "- `How should pandas maintainers handle ...?`\n"
                "- `Remember that ...`"
            )

        except Exception:
            return (
                "One of the chatbot tools is temporarily unavailable, so I could not "
                "complete that tool call right now. The message was still saved."
            )

    async def _call_maybe_async(self, func: Any, **kwargs: Any) -> Any:
        """Call either a sync or async tool function."""
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

    def _is_memory_lookup(self, normalized: str) -> bool:
        """Detect requests that ask what the assistant remembers about the user."""
        memory_lookup_phrases = (
            "what do i prefer",
            "what are my preferences",
            "what is my preference",
            "what did i ask you to remember",
            "what do you remember",
            "do you remember",
            "my preference",
            "my preferences",
            "what do you know about me",
            "what have you saved",
            "what memory do you have",
        )

        return any(phrase in normalized for phrase in memory_lookup_phrases)
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

    def _format_memory_write(self, memory_text: str) -> str:
        """Format explicit long-term memory write confirmation."""
        return (
            "Saved this as long-term memory.\n\n"
            f"Memory saved:\n`{redact_text(memory_text)}`\n\n"
            "This was an explicit memory write, so it was also recorded in the audit log."
        )
    def _format_memory_recall(self, memories: list[Any]) -> str:
        """Format saved long-term memories for the current user."""
        if not memories:
            return (
                "I do not have any saved long-term memories for you yet.\n\n"
                "You can save one explicitly by saying something like:\n"
                "`Remember that this maintainer prefers concise answers.`"
            )

        lines = [
            "Here is what I remember for your maintainer workflow:",
            "",
        ]

        for index, memory in enumerate(memories, start=1):
            memory_type = getattr(memory, "memory_type", "semantic")
            content = redact_text(getattr(memory, "content", ""))

            lines.append(f"{index}. `{memory_type}` memory: {content}")

        lines.extend(
            [
                "",
                "I will use these saved preferences when helping with future maintainer issues.",
            ]
        )

        return "\n".join(lines)

    def _format_classification(self, result: Any) -> str:
        """Format classifier output as a maintainer-friendly triage answer."""
        label = self._read_value(result, "label", "unknown")
        confidence = self._read_value(result, "confidence", None)
        model = self._read_value(result, "model", "classifier")

        confidence_text = "unknown"
        if confidence is not None:
            confidence_text = str(confidence)

        reason = self._classification_reason(label)
        action = self._classification_action(label)

        return (
            f"I would classify this issue as **{label}**.\n\n"
            f"**Confidence:** {confidence_text}\n\n"
            f"**Model used:** `{model}`\n\n"
            f"**Why:** {reason}\n\n"
            f"**Suggested maintainer action:** {action}"
        )

    def _classification_reason(self, label: str) -> str:
        """Return a short explanation for the predicted label."""
        reasons = {
            "bug": (
                "The issue describes broken or unexpected behavior in an existing "
                "feature, especially because it mentions a failure, error, exception, "
                "or incorrect result."
            ),
            "feature": (
                "The issue appears to request new behavior, expanded support, or an "
                "enhancement rather than reporting an existing behavior as broken."
            ),
            "docs": (
                "The issue appears to be about documentation, examples, guides, or "
                "clarifying existing behavior for users."
            ),
            "question": (
                "The issue appears to ask for help or clarification rather than "
                "reporting a confirmed defect or requesting a concrete feature."
            ),
        }

        return reasons.get(label, "The classifier returned a label outside the known set.")

    def _classification_action(self, label: str) -> str:
        """Return a suggested maintainer action for a predicted label."""
        actions = {
            "bug": (
                "Ask for a minimal reproducible example, pandas version, Python version, "
                "expected behavior, actual behavior, and a small input sample if relevant. "
                "If reproducible, keep it labeled as a bug and route it to the relevant area."
            ),
            "feature": (
                "Ask the reporter to clarify the use case, expected API behavior, and "
                "whether there is an existing workaround. Then decide whether it fits "
                "the project roadmap."
            ),
            "docs": (
                "Ask which page or example is confusing, then route it to documentation. "
                "If the fix is small, suggest a docs PR."
            ),
            "question": (
                "Ask for missing context and consider redirecting to support channels if "
                "it is not actionable as a GitHub issue."
            ),
        }

        return actions.get(label, "Review manually before applying a maintainer label.")

    def _format_entities(self, result: Any) -> str:
        """Format NER output as a clean list."""
        entities = self._read_value(result, "entities", [])

        if not entities:
            return (
                "I did not find code-shaped entities in this message.\n\n"
                "Useful entities usually include function names, file names, error types, "
                "package names, versions, commands, or environment variables."
            )

        lines = ["I found these code-shaped entities:\n"]

        for entity in entities:
            if isinstance(entity, dict):
                text = entity.get("text", "")
                entity_type = entity.get("type", "unknown")
                lines.append(f"- `{text}` — {entity_type}")
            else:
                lines.append(f"- `{entity}`")

        lines.append(
            "\nSuggested maintainer action: use these entities to route the issue "
            "to the right subsystem and ask for a minimal reproduction around the "
            "most relevant function, file, or error."
        )

        return "\n".join(lines)

    def _format_summary(self, result: Any) -> str:
        """Format summarizer output as a maintainer thread summary."""
        summary = self._read_value(result, "summary", None)
        resolution = self._read_value(result, "resolution", None)
        open_questions = self._read_value(result, "open_questions", [])

        if not summary:
            summary = str(result)

        if not resolution:
            resolution = "No clear resolution was detected."

        response = (
            "**Thread summary**\n\n"
            f"{summary}\n\n"
            "**Likely resolution/status**\n\n"
            f"{resolution}\n\n"
        )

        if open_questions:
            response += "**Open questions**\n\n"
            for question in open_questions:
                response += f"- {question}\n"
        else:
            response += "**Open questions**\n\n- No obvious open questions detected.\n"

        response += (
            "\nSuggested maintainer action: confirm whether the reporter provided enough "
            "information to reproduce the issue. If not, ask for a minimal reproducible example."
        )

        return response

    def _format_rag_answer(self, result: Any) -> str:
        """Format RAG output as a maintainer-style grounded answer."""
        answer = self._read_value(result, "answer", None)

        if answer:
            return str(answer)

        context = self._read_value(result, "context", None)
        grounding_chunk_ids = self._read_value(result, "grounding_chunk_ids", [])
        rewritten_query = self._read_value(result, "rewritten_query", None)

        if not context:
            return str(result)

        return (
            "**Maintainer guidance**\n\n"
            "Based on the retrieved pandas issue context, I would handle this as a "
            "potential bug triage case first.\n\n"
            "**Recommended next steps**\n\n"
            "1. Ask for a minimal reproducible example.\n"
            "2. Ask for pandas version, Python version, and the exact input or CSV sample.\n"
            "3. Confirm the exact error message and whether the behavior changed between versions.\n"
            "4. If the failure is reproducible, keep it as a bug and route it to the relevant "
            "I/O or parsing area.\n"
            "5. If it is usage-related or caused by malformed input, clarify the expected behavior "
            "and consider documentation follow-up.\n\n"
            f"**Rewritten/retrieval query:** `{rewritten_query or 'not provided'}`\n\n"
            f"**Grounding chunks:** {', '.join(grounding_chunk_ids) if grounding_chunk_ids else 'not provided'}\n\n"
            "**Retrieved context used**\n\n"
            f"{context[:2500]}"
        )

    def _read_value(self, result: Any, key: str, default: Any) -> Any:
        """Read a value from either a dict or an object."""
        if isinstance(result, dict):
            return result.get(key, default)

        return getattr(result, key, default)