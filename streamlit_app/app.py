"""Streamlit internal UI for Maintainer's Copilot.

This is the internal/admin-facing UI.

Current Batch 13 goal:
- working login
- working registration
- authenticated chat
- JWT stored in Streamlit session state
- conversation_id preserved across messages

Visual polish comes later.
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
) -> tuple[bool, dict[str, Any]]:
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
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input(
            "Password",
            type="password",
            key="login_password",
        )

        if st.button("Login"):
            login_user(login_email, login_password)

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


def render_chat() -> None:
    """Render authenticated chat UI."""
    st.subheader("Chat")

    if not st.session_state.token:
        st.info("Login first to use the chatbot.")
        return

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_input = st.chat_input(
        "Ask about pandas issues, classify an issue, summarize a thread, or write memory..."
    )

    if user_input:
        with st.chat_message("user"):
            st.write(user_input)

        send_chat_message(user_input)

        st.rerun()


def render_quick_examples() -> None:
    """Render quick example prompts for testing."""
    st.subheader("Quick test prompts")

    examples = [
        "Classify this issue: read_csv fails with ValueError",
        "Extract entities from this issue: read_csv() fails with ValueError in parser.py",
        "Summarize this thread: User reports read_csv failing. Maintainer asks for reproduction.",
        "How should pandas maintainers handle a read_csv parsing bug?",
        "Remember that this user prefers concise maintainer answers.",
    ]

    for example in examples:
        st.code(example)


def main() -> None:
    """Run the Streamlit app."""
    st.set_page_config(
        page_title="Maintainer's Copilot",
        page_icon="🛠️",
        layout="wide",
    )

    initialize_session_state()

    st.title("Maintainer's Copilot")
    st.caption("Internal Streamlit UI — working version first, visual polish later.")

    render_user_sidebar()

    if not st.session_state.token:
        render_auth_panel()
    else:
        load_current_user()

        left_column, right_column = st.columns([2, 1])

        with left_column:
            render_chat()

        with right_column:
            render_quick_examples()


if __name__ == "__main__":
    main()