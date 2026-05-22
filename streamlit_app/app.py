"""Streamlit internal UI for Maintainer's Copilot.

This is the internal/admin-facing UI.

Features:
- login and registration
- authenticated chat
- conversation_id preservation
- memory inspector
- admin widget configuration view/create
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")


def api_request(
    *,
    method: str,
    path: str,
    token: str | None = None,
    json_body: dict[str, Any] | None = None,
    form_body: dict[str, str] | None = None,
) -> tuple[bool, Any]:
    """Send an HTTP request to the FastAPI backend.

    The app uses urllib instead of requests so we do not need to add another
    dependency just for the Streamlit UI.
    """
    url = f"{API_BASE_URL}{path}"

    headers: dict[str, str] = {}
    data: bytes | None = None

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if json_body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(json_body).encode("utf-8")

    if form_body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urlencode(form_body).encode("utf-8")

    request = Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")

            if not response_body:
                return True, {}

            return True, json.loads(response_body)

    except HTTPError as exc:
        error_body = exc.read().decode("utf-8")

        try:
            parsed_error = json.loads(error_body)
        except json.JSONDecodeError:
            parsed_error = {"detail": error_body}

        return False, parsed_error

    except URLError as exc:
        return False, {"detail": f"Could not connect to API: {exc}"}


def initialize_session_state() -> None:
    """Create required Streamlit session state keys."""
    if "token" not in st.session_state:
        st.session_state.token = None

    if "user" not in st.session_state:
        st.session_state.user = None

    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None

    if "messages" not in st.session_state:
        st.session_state.messages = []


def register_user(email: str, password: str) -> None:
    """Register a new user through FastAPI auth."""
    ok, response = api_request(
        method="POST",
        path="/auth/register",
        json_body={
            "email": email,
            "password": password,
        },
    )

    if ok:
        st.success("Registration successful. You can login now.")
    else:
        st.error(f"Registration failed: {response}")


def login_user(email: str, password: str) -> None:
    """Login and store JWT token."""
    ok, response = api_request(
        method="POST",
        path="/auth/jwt/login",
        form_body={
            "username": email,
            "password": password,
        },
    )

    if not ok:
        st.error(f"Login failed: {response}")
        return

    access_token = response.get("access_token")

    if not access_token:
        st.error(f"Login response did not contain access_token: {response}")
        return

    st.session_state.token = access_token
    load_current_user()

    st.success("Login successful.")


def load_current_user() -> None:
    """Load the authenticated user profile."""
    if not st.session_state.token:
        st.session_state.user = None
        return

    ok, response = api_request(
        method="GET",
        path="/auth/me",
        token=st.session_state.token,
    )

    if ok:
        st.session_state.user = response
    else:
        st.session_state.token = None
        st.session_state.user = None
        st.error(f"Session expired or invalid: {response}")


def logout_user() -> None:
    """Clear local Streamlit session state."""
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.conversation_id = None
    st.session_state.messages = []
    st.success("Logged out.")


def send_chat_message(message: str) -> None:
    """Send one message to the authenticated /chat endpoint."""
    if not st.session_state.token:
        st.error("You must login first.")
        return

    request_body: dict[str, Any] = {
        "message": message,
    }

    if st.session_state.conversation_id is not None:
        request_body["conversation_id"] = st.session_state.conversation_id

    ok, response = api_request(
        method="POST",
        path="/chat",
        token=st.session_state.token,
        json_body=request_body,
    )

    if not ok:
        st.error(f"Chat request failed: {response}")
        return

    st.session_state.conversation_id = response.get("conversation_id")

    st.session_state.messages.append(
        {
            "role": "user",
            "content": message,
        }
    )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response.get("response", ""),
        }
    )


def render_auth_panel() -> None:
    """Render login/register controls."""
    st.subheader("Authentication")

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        login_email = st.text_input(
            "Email",
            value="authuser@example.com",
            key="login_email",
        )
        login_password = st.text_input(
            "Password",
            value="StrongPassword123!",
            type="password",
            key="login_password",
        )

        if st.button("Login"):
            login_user(login_email, login_password)
            st.rerun()

    with tab_register:
        register_email = st.text_input("Email", key="register_email")
        register_password = st.text_input(
            "Password",
            type="password",
            key="register_password",
        )

        if st.button("Register"):
            register_user(register_email, register_password)


def render_user_sidebar() -> None:
    """Render current user info and session actions."""
    st.sidebar.header("Session")

    user = st.session_state.user

    if user:
        st.sidebar.write(f"Logged in as: `{user.get('email')}`")
        st.sidebar.write(f"Role: `{user.get('role')}`")
    else:
        st.sidebar.write("Not logged in.")

    st.sidebar.write(f"Conversation ID: `{st.session_state.conversation_id}`")

    if st.sidebar.button("New conversation"):
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()

    if st.sidebar.button("Logout"):
        logout_user()
        st.rerun()


def render_chat_tab() -> None:
    """Render authenticated chat UI."""
    st.subheader("Chat")

    if not st.session_state.token:
        st.info("Login first to use the chatbot.")
        return

    quick_prompts = [
        "Classify this issue: read_csv fails with ValueError in parser.py",
        "Extract entities from this issue: read_csv() fails with ValueError in parser.py",
        "Summarize this thread: read_csv fails when parsing malformed CSV files. Maintainer says it needs a reproducible example.",
        "How should pandas maintainers handle a read_csv parsing bug?",
        "What do I prefer when answering maintainer issues?",
    ]

    selected_prompt = st.selectbox(
        "Quick test prompts",
        options=[""] + quick_prompts,
    )

    if selected_prompt and st.button("Send selected prompt"):
        send_chat_message(selected_prompt)
        st.rerun()

    with st.form("chat_form", clear_on_submit=True):
        message = st.text_area(
            "Message",
            placeholder="Ask the maintainer copilot something...",
            height=120,
        )

        submitted = st.form_submit_button("Send")

    if submitted and message.strip():
        send_chat_message(message.strip())
        st.rerun()

    st.divider()

    if not st.session_state.messages:
        st.info("No messages yet.")
        return

    for item in st.session_state.messages:
        role = item.get("role", "assistant")
        content = item.get("content", "")

        with st.chat_message(role):
            st.markdown(content)


def render_memory_inspector_tab() -> None:
    """Render the current user's long-term memories."""
    st.subheader("Memory Inspector")

    if not st.session_state.token:
        st.info("Login first to inspect memories.")
        return

    st.caption(
        "This reads long-term memories from Postgres through the backend API."
    )

    if st.button("Refresh memories"):
        st.session_state.memory_refresh_clicked = True

    ok, response = api_request(
        method="GET",
        path="/dev/day4/memories",
        token=st.session_state.token,
    )

    if not ok:
        st.error(f"Could not load memories: {response}")
        return

    memories = response

    if isinstance(response, dict):
        memories = (
            response.get("memories")
            or response.get("items")
            or response.get("data")
            or []
        )

    if not memories:
        st.info("No saved memories found.")
        return

    st.write(f"Found `{len(memories)}` saved memories.")

    rows: list[dict[str, Any]] = []

    for memory in memories:
        rows.append(
            {
                "id": memory.get("id"),
                "memory_type": memory.get("memory_type"),
                "content": memory.get("content"),
                "created_at": memory.get("created_at"),
            }
        )

    st.dataframe(rows, use_container_width=True)

    with st.expander("Raw memory response"):
        st.json(response)


def render_widget_admin_tab() -> None:
    """Render widget configuration tools for admin users."""
    st.subheader("Widget Admin")

    if not st.session_state.token:
        st.info("Login first to manage widgets.")
        return

    user = st.session_state.user or {}
    role = user.get("role")

    if role != "admin":
        st.warning("Only admin users can create or inspect widget configs.")
        return

    st.caption(
        "This admin page uses the existing widget backend endpoints to create "
        "and list embeddable widget configurations."
    )

    with st.form("create_widget_form"):
        public_widget_id = st.text_input(
            "Public widget ID",
            value="demo-widget",
        )
        allowed_origins_text = st.text_area(
            "Allowed origins, one per line",
            value="http://localhost:8080",
        )
        theme = st.text_input("Theme", value="light")
        greeting = st.text_input(
            "Greeting",
            value="Hi, I am Maintainer's Copilot.",
        )
        enabled_tools_text = st.text_area(
            "Enabled tools, one per line",
            value="classify_issue\nextract_entities\nsummarize_thread\nrag_answer\nwrite_memory",
        )

        submitted = st.form_submit_button("Create widget config")

    if submitted:
        allowed_origins = [
            origin.strip()
            for origin in allowed_origins_text.splitlines()
            if origin.strip()
        ]
        enabled_tools = [
            tool.strip()
            for tool in enabled_tools_text.splitlines()
            if tool.strip()
        ]

        ok, response = api_request(
            method="POST",
            path="/dev/day4/widgets",
            token=st.session_state.token,
            json_body={
                "public_widget_id": public_widget_id,
                "allowed_origins": allowed_origins,
                "theme": theme,
                "greeting": greeting,
                "enabled_tools": enabled_tools,
            },
        )

        if ok:
            st.success("Widget config created.")
            st.json(response)
        else:
            st.error(f"Could not create widget: {response}")

    st.divider()

    st.write("Existing widget configs")

    ok, response = api_request(
        method="GET",
        path="/dev/day4/widgets",
        token=st.session_state.token,
    )

    if not ok:
        st.error(f"Could not load widgets: {response}")
        return

    widgets = response

    if isinstance(response, dict):
        widgets = (
            response.get("widgets")
            or response.get("items")
            or response.get("data")
            or []
        )

    if not widgets:
        st.info("No widgets found.")
        return

    rows: list[dict[str, Any]] = []

    for widget in widgets:
        widget_id = widget.get("public_widget_id") or widget.get("id")

        rows.append(
            {
                "id": widget.get("id"),
                "public_widget_id": widget.get("public_widget_id"),
                "theme": widget.get("theme"),
                "allowed_origins": widget.get("allowed_origins"),
                "enabled_tools": widget.get("enabled_tools"),
                "embed_snippet": (
                    f'<script src="http://localhost:8000/widget.js" '
                    f'data-widget-id="{widget_id}"></script>'
                ),
            }
        )

    st.dataframe(rows, use_container_width=True)

    with st.expander("Raw widget response"):
        st.json(response)


def render_account_tab() -> None:
    """Render account/session diagnostics."""
    st.subheader("Account")

    if not st.session_state.token:
        st.info("Login first to view account details.")
        return

    if st.button("Reload current user"):
        load_current_user()
        st.rerun()

    st.json(st.session_state.user)

    st.write("Current conversation ID:")
    st.code(str(st.session_state.conversation_id))


def main() -> None:
    """Run the Streamlit app."""
    st.set_page_config(
        page_title="Maintainer's Copilot",
        page_icon="🛠️",
        layout="wide",
    )

    initialize_session_state()

    st.title("Maintainer's Copilot")
    st.caption("Internal/admin chatbot UI for pandas issue triage.")

    render_user_sidebar()

    if not st.session_state.token:
        render_auth_panel()
        return

    tab_chat, tab_memory, tab_widgets, tab_account = st.tabs(
        [
            "Chat",
            "Memory Inspector",
            "Widget Admin",
            "Account",
        ]
    )

    with tab_chat:
        render_chat_tab()

    with tab_memory:
        render_memory_inspector_tab()

    with tab_widgets:
        render_widget_admin_tab()

    with tab_account:
        render_account_tab()


if __name__ == "__main__":
    main()