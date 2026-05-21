import React, { useEffect, useMemo, useState } from "react";

const API_BASE_URL =
  window.__MAINTAINERS_COPILOT_API_URL__ || "http://localhost:8000";

const QUICK_ACTIONS = [
  "Classify this issue: read_csv fails with ValueError in parser.py",
  "Extract entities from this issue: read_csv() fails with ValueError in parser.py",
  "How should pandas maintainers handle a read_csv parsing bug?"
];

function formatMessage(text) {
  // Lightweight markdown support for demo-friendly chatbot responses.
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br />");
}

export default function App() {
  const [isOpen, setIsOpen] = useState(false);
  const [email, setEmail] = useState("authuser@example.com");
  const [password, setPassword] = useState("StrongPassword123!");
  const [token, setToken] = useState("");
  const [conversationId, setConversationId] = useState(null);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi, I am Maintainer's Copilot. I can classify issues, extract code-shaped entities, summarize threads, and answer RAG questions."
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const widgetHeight = useMemo(() => {
    return isOpen ? 620 : 76;
  }, [isOpen]);

  useEffect(() => {
    // The host loader listens to this event and resizes the iframe.
    window.parent.postMessage(
      {
        type: "maintainers-copilot:resize",
        height: widgetHeight,
        width: isOpen ? 380 : 76
      },
      "*"
    );
  }, [widgetHeight, isOpen]);

  async function login() {
    setError("");
    setIsLoading(true);

    try {
      const body = new URLSearchParams();
      body.append("username", email);
      body.append("password", password);

      const response = await fetch(`${API_BASE_URL}/auth/jwt/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded"
        },
        body
      });

      if (!response.ok) {
        throw new Error("Login failed. Check the email/password or API status.");
      }

      const data = await response.json();
      setToken(data.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function sendChat(customMessage) {
    const outgoing = customMessage || message.trim();

    if (!outgoing) {
      return;
    }

    if (!token) {
      setError("Please login before chatting.");
      return;
    }

    setError("");
    setIsLoading(true);
    setMessage("");

    setMessages((current) => [
      ...current,
      {
        role: "user",
        content: outgoing
      }
    ]);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          message: outgoing,
          conversation_id: conversationId
        })
      });

      if (!response.ok) {
        throw new Error("Chat request failed. Check API logs.");
      }

      const data = await response.json();

      if (data.conversation_id) {
        setConversationId(data.conversation_id);
      }

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: data.response || data.message || JSON.stringify(data, null, 2)
        }
      ]);
    } catch (err) {
      setError(err.message);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            "I could not complete the request. Please check that the API is running and that you are logged in."
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  if (!isOpen) {
    return (
      <>
        <style>{styles}</style>
        <button
          className="mc-bubble"
          onClick={() => setIsOpen(true)}
          aria-label="Open Maintainer's Copilot"
        >
          MC
        </button>
      </>
    );
  }

  return (
    <>
      <style>{styles}</style>

      <section className="mc-panel">
        <header className="mc-header">
          <div>
            <div className="mc-title">Maintainer's Copilot</div>
            <div className="mc-subtitle">pandas issue triage assistant</div>
          </div>

          <button
            className="mc-minimize"
            onClick={() => setIsOpen(false)}
            aria-label="Minimize widget"
          >
            —
          </button>
        </header>

        {!token && (
          <div className="mc-login">
            <label>
              Email
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="authuser@example.com"
              />
            </label>

            <label>
              Password
              <input
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                placeholder="Password"
              />
            </label>

            <button className="mc-primary" onClick={login} disabled={isLoading}>
              {isLoading ? "Logging in..." : "Login"}
            </button>
          </div>
        )}

        {token && (
          <>
            <div className="mc-status">Authenticated widget session</div>

            <div className="mc-quick-actions">
              {QUICK_ACTIONS.map((action) => (
                <button
                  key={action}
                  onClick={() => sendChat(action)}
                  disabled={isLoading}
                >
                  {action}
                </button>
              ))}
            </div>
          </>
        )}

        <main className="mc-messages">
          {messages.map((item, index) => (
            <div key={`${item.role}-${index}`} className={`mc-msg ${item.role}`}>
              <div className="mc-role">{item.role}</div>
              <div
                className="mc-content"
                dangerouslySetInnerHTML={{
                  __html: formatMessage(item.content)
                }}
              />
            </div>
          ))}

          {isLoading && <div className="mc-loading">Working...</div>}
        </main>

        {error && <div className="mc-error">{error}</div>}

        <footer className="mc-input-row">
          <input
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                sendChat();
              }
            }}
            placeholder="Ask about a pandas issue..."
            disabled={!token || isLoading}
          />

          <button
            className="mc-send"
            onClick={() => sendChat()}
            disabled={!token || isLoading}
          >
            Send
          </button>
        </footer>
      </section>
    </>
  );
}

const styles = `
  :root {
    color-scheme: light;
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }

  * {
    box-sizing: border-box;
  }

  body {
    margin: 0;
    background: transparent;
  }

  .mc-bubble {
    width: 64px;
    height: 64px;
    border: none;
    border-radius: 999px;
    background: #111827;
    color: white;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.22);
  }

  .mc-panel {
    width: 360px;
    height: 600px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    background: #ffffff;
    color: #111827;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.22);
  }

  .mc-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 14px;
    background: #111827;
    color: #ffffff;
  }

  .mc-title {
    font-size: 15px;
    font-weight: 800;
  }

  .mc-subtitle {
    margin-top: 2px;
    font-size: 12px;
    opacity: 0.78;
  }

  .mc-minimize {
    width: 32px;
    height: 32px;
    border: none;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.12);
    color: white;
    cursor: pointer;
    font-size: 18px;
  }

  .mc-login {
    display: grid;
    gap: 10px;
    padding: 12px;
    border-bottom: 1px solid #eef2f7;
  }

  .mc-login label {
    display: grid;
    gap: 4px;
    font-size: 12px;
    font-weight: 700;
    color: #374151;
  }

  .mc-login input,
  .mc-input-row input {
    width: 100%;
    border: 1px solid #d1d5db;
    border-radius: 11px;
    padding: 10px 11px;
    font-size: 13px;
    outline: none;
  }

  .mc-login input:focus,
  .mc-input-row input:focus {
    border-color: #111827;
  }

  .mc-primary,
  .mc-send {
    border: none;
    border-radius: 11px;
    background: #111827;
    color: white;
    padding: 10px 12px;
    font-weight: 800;
    cursor: pointer;
  }

  .mc-primary:disabled,
  .mc-send:disabled,
  .mc-quick-actions button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .mc-status {
    margin: 10px 12px 0;
    padding: 8px 10px;
    border-radius: 11px;
    background: #ecfdf5;
    color: #065f46;
    font-size: 12px;
    font-weight: 700;
  }

  .mc-quick-actions {
    display: grid;
    gap: 7px;
    padding: 10px 12px;
    border-bottom: 1px solid #eef2f7;
  }

  .mc-quick-actions button {
    border: 1px solid #e5e7eb;
    border-radius: 11px;
    background: #f9fafb;
    color: #1f2937;
    padding: 8px 9px;
    cursor: pointer;
    font-size: 12px;
    text-align: left;
  }

  .mc-messages {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 10px;
    overflow-y: auto;
    padding: 12px;
    background: #f8fafc;
  }

  .mc-msg {
    max-width: 92%;
    padding: 10px 11px;
    border-radius: 14px;
    font-size: 13px;
    line-height: 1.42;
  }

  .mc-msg.assistant {
    align-self: flex-start;
    background: #ffffff;
    border: 1px solid #e5e7eb;
  }

  .mc-msg.user {
    align-self: flex-end;
    background: #111827;
    color: #ffffff;
  }

  .mc-role {
    margin-bottom: 5px;
    font-size: 10px;
    font-weight: 900;
    text-transform: uppercase;
    opacity: 0.65;
  }

  .mc-content code {
    border-radius: 6px;
    padding: 1px 4px;
    background: rgba(148, 163, 184, 0.18);
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }

  .mc-loading {
    font-size: 12px;
    color: #6b7280;
  }

  .mc-error {
    margin: 8px 12px 0;
    padding: 9px 10px;
    border-radius: 11px;
    background: #fef2f2;
    color: #991b1b;
    font-size: 12px;
    font-weight: 700;
  }

  .mc-input-row {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 8px;
    padding: 12px;
    border-top: 1px solid #e5e7eb;
    background: #ffffff;
  }
`;
