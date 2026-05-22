import React, { useEffect, useMemo, useState } from "react";

const API_BASE_URL =
  window.__MAINTAINERS_COPILOT_API_URL__ || "http://localhost:8000";

function getWidgetIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("widget_id") || "demo-widget";
}

const DEFAULT_WIDGET_CONFIG = {
  public_widget_id: "demo-widget",
  greeting:
    "Hi, I am Maintainer's Copilot. I can classify issues, extract code-shaped entities, summarize threads, and answer RAG questions.",
  theme: {
    primaryColor: "#111827",
    position: "bottom-right"
  },
  enabled_tools: [
    "classify_issue",
    "extract_entities",
    "summarize_thread",
    "rag_answer",
    "write_memory"
  ]
};

const QUICK_ACTIONS = [
  {
    tool: "classify_issue",
    label: "Classify issue",
    message: "Classify this issue: read_csv fails with ValueError in parser.py"
  },
  {
    tool: "extract_entities",
    label: "Extract entities",
    message: "Extract entities from this issue: read_csv() fails with ValueError in parser.py"
  },
  {
    tool: "summarize_thread",
    label: "Summarize thread",
    message:
      "Summarize this thread: read_csv fails when parsing malformed CSV files. Maintainer says it needs a reproducible example."
  },
  {
    tool: "rag_answer",
    label: "RAG guidance",
    message: "How should pandas maintainers handle a read_csv parsing bug?"
  },
  {
    tool: "write_memory",
    label: "Memory test",
    message:
      "Remember that this maintainer prefers concise answers with reproduction steps."
  }
];

function formatMessage(text) {
  return String(text || "")
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
  const [messages, setMessages] = useState([]);
  const [widgetConfig, setWidgetConfig] = useState(DEFAULT_WIDGET_CONFIG);
  const [widgetConfigStatus, setWidgetConfigStatus] = useState(
    "Using default widget config."
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const widgetHeight = useMemo(() => {
    return isOpen ? 620 : 76;
  }, [isOpen]);

  const widgetWidth = useMemo(() => {
    return isOpen ? 380 : 76;
  }, [isOpen]);

  const primaryColor = widgetConfig.theme?.primaryColor || "#111827";

  const quickActions = QUICK_ACTIONS.filter((action) => {
    return widgetConfig.enabled_tools?.includes(action.tool);
  });

  useEffect(() => {
    async function loadWidgetConfig() {
      const widgetId = getWidgetIdFromUrl();

      try {
        const response = await fetch(
          `${API_BASE_URL}/widgets/public/${encodeURIComponent(widgetId)}`
        );

        if (!response.ok) {
          setWidgetConfigStatus(
            `Widget config '${widgetId}' was not found. Using default config.`
          );
          return;
        }

        const config = await response.json();

        setWidgetConfig({
          ...DEFAULT_WIDGET_CONFIG,
          ...config,
          theme: {
            ...DEFAULT_WIDGET_CONFIG.theme,
            ...(config.theme || {})
          },
          enabled_tools:
            config.enabled_tools || DEFAULT_WIDGET_CONFIG.enabled_tools
        });

        setWidgetConfigStatus(`Loaded widget config '${widgetId}'.`);
      } catch (err) {
        setWidgetConfigStatus(
          "Could not load widget config from API. Using default config."
        );
      }
    }

    loadWidgetConfig();
  }, []);

  useEffect(() => {
    setMessages((current) => {
      if (current.length > 0) {
        return current;
      }

      return [
        {
          role: "assistant",
          content: widgetConfig.greeting
        }
      ];
    });
  }, [widgetConfig.greeting]);

  useEffect(() => {
    window.parent.postMessage(
      {
        type: "maintainers-copilot:resize",
        height: widgetHeight,
        width: widgetWidth
      },
      "*"
    );
  }, [widgetHeight, widgetWidth]);

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
      setError(err.message || "Login failed.");
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
      setError(err.message || "Chat request failed.");
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
      <div style={{ "--mc-primary": primaryColor }}>
        <style>{styles}</style>
        <button
          className="mc-bubble"
          onClick={() => setIsOpen(true)}
          aria-label="Open Maintainer's Copilot"
        >
          MC
        </button>
      </div>
    );
  }

  return (
    <div style={{ "--mc-primary": primaryColor }}>
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
            <div className="mc-config-status">{widgetConfigStatus}</div>

            <div className="mc-quick-actions">
              {quickActions.length === 0 && (
                <div className="mc-empty-tools">
                  No quick actions enabled for this widget.
                </div>
              )}

              {quickActions.map((action) => (
                <button
                  key={action.message}
                  onClick={() => sendChat(action.message)}
                  disabled={isLoading}
                  title={action.tool}
                >
                  {action.label}
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
    </div>
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
    background: var(--mc-primary, #111827);
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
    background: var(--mc-primary, #111827);
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
    border-color: var(--mc-primary, #111827);
  }

  .mc-primary,
  .mc-send {
    border: none;
    border-radius: 11px;
    background: var(--mc-primary, #111827);
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

  .mc-config-status {
    margin: 6px 12px 0;
    color: #6b7280;
    font-size: 11px;
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

  .mc-empty-tools {
    color: #6b7280;
    font-size: 12px;
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
    background: var(--mc-primary, #111827);
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
`