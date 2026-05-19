"""Issue thread summarization logic for the model server.

This file owns the summarization function used by the /summarize endpoint.

The final project can use:
- an LLM-driven summarizer
- or a pretrained summarization model

For now, this file provides a lightweight placeholder summarizer so the
model server can expose a working endpoint early.
"""

from model_server.schemas import SummarizeThreadRequest, SummarizeThreadResponse


MAX_SUMMARY_CHARS = 500


def build_thread_text(request: SummarizeThreadRequest) -> str:
    """Combine title, body, and comments into one thread text.

    The title gives the main topic.
    The body gives the original issue details.
    Comments may include debugging discussion, maintainer replies, and resolution.
    """
    parts = [f"Title: {request.title}"]

    if request.body:
        parts.append(f"Body: {request.body}")

    for index, comment in enumerate(request.comments, start=1):
        parts.append(f"Comment {index}: {comment}")

    return "\n\n".join(parts)


def make_short_summary(text: str) -> str:
    """Create a short placeholder summary from the thread text.

    This is not advanced summarization yet.
    It simply keeps the first part of the issue thread so the endpoint has
    a predictable response during integration.
    """
    cleaned_text = " ".join(text.split())

    if len(cleaned_text) <= MAX_SUMMARY_CHARS:
        return cleaned_text

    return cleaned_text[:MAX_SUMMARY_CHARS].rstrip() + "..."


def detect_resolution(comments: list[str]) -> str | None:
    """Try to detect a simple resolution from issue comments.

    This placeholder looks for common words that suggest the issue was fixed,
    closed, or answered.
    """
    resolution_keywords = ["fixed", "resolved", "closed", "answered", "merged"]

    for comment in reversed(comments):
        lower_comment = comment.lower()

        if any(keyword in lower_comment for keyword in resolution_keywords):
            return comment

    return None


def summarize_thread(request: SummarizeThreadRequest) -> SummarizeThreadResponse:
    """Summarize an issue thread.

    This function is called by the /summarize endpoint.

    Later replacement:
    The inside of this function can call an LLM using a prompt stored in
    prompts/summarize_thread.md.
    """
    thread_text = build_thread_text(request)

    return SummarizeThreadResponse(
        summary=make_short_summary(thread_text),
        resolution=detect_resolution(request.comments),
        open_questions=[],
    )