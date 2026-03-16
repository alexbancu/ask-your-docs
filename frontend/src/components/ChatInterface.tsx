import { useEffect, useRef, useState } from "react";
import type { Message } from "../types";
import { askQuestionStream } from "../api/client";
import ExampleChips from "./ExampleChips";
import MessageBubble from "./MessageBubble";

interface ChatInterfaceProps {
  onOpenSidebar: () => void;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  onConversationUpdate: (messages: Message[]) => void;
}

export default function ChatInterface({
  onOpenSidebar,
  messages,
  setMessages,
  onConversationUpdate,
}: ChatInterfaceProps) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Focus input on / key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "/" && document.activeElement !== inputRef.current) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const handleSubmit = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: question.trim(),
    };

    const assistantId = crypto.randomUUID();

    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantId, role: "assistant", content: "", isStreaming: true },
    ]);
    setInput("");
    setLoading(true);
    setTimeout(scrollToBottom, 100);

    try {
      await askQuestionStream(question.trim(), {
        onSources: (sources, confidence) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, sources, confidence } : m,
            ),
          );
          setTimeout(scrollToBottom, 100);
        },
        onToken: (token) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content + token }
                : m,
            ),
          );
          setTimeout(scrollToBottom, 100);
        },
        onDone: () => {
          setMessages((prev) => {
            const updated = prev.map((m) =>
              m.id === assistantId ? { ...m, isStreaming: false } : m,
            );
            onConversationUpdate(updated);
            return updated;
          });
        },
      });
    } catch {
      setMessages((prev) => {
        const updated = prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: "Something went wrong. Please try again.",
                confidence: "low" as const,
                isStreaming: false,
              }
            : m,
        );
        onConversationUpdate(updated);
        return updated;
      });
    } finally {
      setLoading(false);
      setTimeout(scrollToBottom, 100);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void handleSubmit(input);
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header */}
      <header
        className="flex shrink-0 items-center gap-3 px-4 py-3 md:px-6"
        style={{ borderBottom: "1px solid var(--color-border-subtle)" }}
      >
        <button
          onClick={onOpenSidebar}
          className="rounded-lg p-1.5 transition-colors md:hidden"
          style={{ color: "var(--color-text-secondary)" }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-surface-overlay)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
          aria-label="Open sidebar"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>
        <div className="flex items-center gap-2">
          <span
            className="text-[15px] font-semibold tracking-tight"
            style={{ color: "var(--color-text-primary)" }}
          >
            Acme Corp
          </span>
          <span
            className="rounded-full px-2 py-0.5 text-[10px] font-medium"
            style={{
              background: "var(--color-accent-muted)",
              color: "var(--color-accent)",
            }}
          >
            Knowledge Base
          </span>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[720px] px-4 py-6 md:px-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center pt-[12vh]">
              <h1
                className="text-center text-4xl leading-tight sm:text-5xl"
                style={{
                  fontFamily: "var(--font-serif)",
                  color: "var(--color-text-primary)",
                }}
              >
                What would you
                <br />
                like to know?
              </h1>
              <p
                className="mt-3 max-w-md text-center text-[15px] leading-relaxed"
                style={{ color: "var(--color-text-secondary)" }}
              >
                Ask anything about Acme Corp — policies, engineering processes,
                security standards, and more.
              </p>
              <div className="mt-10 w-full max-w-lg">
                <ExampleChips onSelect={(q) => void handleSubmit(q)} />
              </div>
              <p
                className="mt-8 text-[12px]"
                style={{ color: "var(--color-text-tertiary)" }}
              >
                5 documents indexed · 83 knowledge chunks
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((msg, i) => (
                <MessageBubble key={msg.id} message={msg} index={i} />
              ))}
            </div>
          )}

          {/* Shimmer removed — streaming MessageBubble handles the loading state */}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div
        className="shrink-0 px-4 py-3 md:px-6"
        style={{ borderTop: "1px solid var(--color-border-subtle)" }}
      >
        <form
          onSubmit={handleFormSubmit}
          className="mx-auto flex max-w-[720px] items-center gap-2"
        >
          <div
            className="relative flex flex-1 items-center rounded-xl transition-colors duration-150"
            style={{
              background: "var(--color-surface-raised)",
              border: "1px solid var(--color-border)",
            }}
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              disabled={loading}
              className="flex-1 bg-transparent px-4 py-3 text-[15px] outline-none placeholder:opacity-40"
              style={{ color: "var(--color-text-primary)" }}
            />
            {!input && (
              <kbd
                className="mr-3 hidden rounded px-1.5 py-0.5 text-[10px] font-medium sm:block"
                style={{
                  background: "var(--color-surface-overlay)",
                  color: "var(--color-text-tertiary)",
                  border: "1px solid var(--color-border)",
                }}
              >
                /
              </kbd>
            )}
          </div>
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-xl px-4 py-3 text-sm font-medium transition-all duration-150 disabled:opacity-30"
            style={{
              background: "var(--color-accent)",
              color: "#fff",
            }}
            onMouseEnter={(e) => {
              if (!e.currentTarget.disabled) {
                e.currentTarget.style.background = "var(--color-accent-hover)";
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "var(--color-accent)";
            }}
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
