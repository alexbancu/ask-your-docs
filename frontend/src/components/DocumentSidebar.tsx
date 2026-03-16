import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import type { Conversation, DocumentInfo } from "../types";
import { getDocuments } from "../api/client";
import { TYPE_STYLES, DEFAULT_STYLE } from "../constants/styles";
import { timeAgo } from "../constants/time";

interface DocumentSidebarProps {
  open: boolean;
  onToggle: () => void;
  onNavigate: () => void;
  conversations: Conversation[];
  activeConversationId: string | null;
  onLoadConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onNewChat: () => void;
}

export default function DocumentSidebar({
  open,
  onToggle,
  onNavigate,
  conversations,
  activeConversationId,
  onLoadConversation,
  onDeleteConversation,
  onNewChat,
}: DocumentSidebarProps) {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [error, setError] = useState(false);
  const location = useLocation();

  useEffect(() => {
    getDocuments()
      .then((res) => setDocuments(res.documents))
      .catch(() => setError(true));
  }, []);

  const content = (
    <div className="flex h-full flex-col">
      {/* Sidebar header */}
      <div
        className="flex shrink-0 items-center justify-between px-4 py-3"
        style={{ borderBottom: "1px solid var(--color-border-subtle)" }}
      >
        <span
          className="text-[13px] font-semibold uppercase tracking-wider"
          style={{ color: "var(--color-text-tertiary)" }}
        >
          Menu
        </span>
        <button
          onClick={onToggle}
          className="rounded-md p-1 transition-colors md:hidden"
          style={{ color: "var(--color-text-tertiary)" }}
          aria-label="Close sidebar"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3">
        {/* New Chat button */}
        <button
          onClick={onNewChat}
          className="mb-3 flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-colors duration-150"
          style={{
            color: "var(--color-accent)",
            border: "1px solid var(--color-border)",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-surface-overlay)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Chat
        </button>

        {/* Recent Chats */}
        {conversations.length > 0 && (
          <div className="mb-4">
            <span
              className="mb-1.5 block px-1 text-[11px] font-semibold uppercase tracking-wider"
              style={{ color: "var(--color-text-tertiary)" }}
            >
              Recent Chats
            </span>
            <div className="space-y-0.5">
              {conversations.map((convo) => {
                const isActive = convo.id === activeConversationId;
                return (
                  <div
                    key={convo.id}
                    className="group relative"
                  >
                    <button
                      onClick={() => onLoadConversation(convo.id)}
                      className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left transition-colors duration-150"
                      style={{
                        background: isActive ? "var(--color-surface-overlay)" : "transparent",
                      }}
                      onMouseEnter={(e) => {
                        if (!isActive) e.currentTarget.style.background = "var(--color-surface-overlay)";
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive) e.currentTarget.style.background = "transparent";
                      }}
                    >
                      <svg
                        className="h-3.5 w-3.5 shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        style={{ color: isActive ? "var(--color-accent)" : "var(--color-text-tertiary)" }}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                      </svg>
                      <div className="min-w-0 flex-1">
                        <p
                          className="truncate text-[13px] font-medium"
                          style={{ color: "var(--color-text-primary)" }}
                        >
                          {convo.title}
                        </p>
                        <span className="text-[11px]" style={{ color: "var(--color-text-tertiary)" }}>
                          {timeAgo(convo.updatedAt)}
                        </span>
                      </div>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(convo.id);
                      }}
                      className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md p-1 opacity-0 transition-opacity group-hover:opacity-100"
                      style={{ color: "var(--color-text-tertiary)" }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = "var(--color-red-text)")}
                      onMouseLeave={(e) => (e.currentTarget.style.color = "var(--color-text-tertiary)")}
                      aria-label="Delete conversation"
                    >
                      <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Documents section */}
        <div>
          <span
            className="mb-1.5 block px-1 text-[11px] font-semibold uppercase tracking-wider"
            style={{ color: "var(--color-text-tertiary)" }}
          >
            Documents
          </span>
          {error ? (
            <p className="px-1 text-[13px]" style={{ color: "var(--color-red-text)" }}>
              Failed to load
            </p>
          ) : documents.length === 0 ? (
            <div className="space-y-2 px-1">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-10 rounded-lg animate-shimmer" />
              ))}
            </div>
          ) : (
            <div className="space-y-1">
              {documents.map((doc) => {
                const style = TYPE_STYLES[doc.document_type] ?? DEFAULT_STYLE;
                const isActive = location.pathname === `/documents/${doc.slug}`;
                return (
                  <Link
                    key={doc.name}
                    to={`/documents/${doc.slug}`}
                    onClick={onNavigate}
                    className="flex items-center gap-2.5 rounded-lg px-2.5 py-2 transition-colors duration-150"
                    style={{
                      background: isActive ? "var(--color-surface-overlay)" : "transparent",
                      textDecoration: "none",
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) e.currentTarget.style.background = "var(--color-surface-overlay)";
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) e.currentTarget.style.background = "transparent";
                    }}
                  >
                    <div
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-xs"
                      style={{ background: style.bg }}
                    >
                      {style.icon}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p
                        className="truncate text-[13px] font-medium"
                        style={{ color: "var(--color-text-primary)" }}
                      >
                        {doc.name}
                      </p>
                      <div className="flex items-center gap-1 text-[11px]" style={{ color: "var(--color-text-tertiary)" }}>
                        <span>
                          {doc.page_count} section{doc.page_count !== 1 ? "s" : ""} ·{" "}
                          <span style={{ color: style.text }}>{doc.document_type}</span>
                        </span>
                        {doc.last_updated && (
                          <>
                            <span className="mx-0.5">·</span>
                            <span
                              className="inline-block h-1.5 w-1.5 rounded-full"
                              style={{ background: doc.is_stale ? "var(--color-orange-text)" : "#22C55E" }}
                            />
                            <span>{doc.last_updated}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Sidebar footer */}
      <div
        className="shrink-0 px-4 py-3"
        style={{ borderTop: "1px solid var(--color-border-subtle)" }}
      >
        <div className="flex items-center gap-2">
          <div
            className="h-2 w-2 rounded-full"
            style={{ background: "#22C55E" }}
          />
          <span className="text-[11px]" style={{ color: "var(--color-text-tertiary)" }}>
            {documents.length} documents indexed
          </span>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className="hidden w-60 shrink-0 md:block"
        style={{
          background: "var(--color-surface-raised)",
          borderRight: "1px solid var(--color-border-subtle)",
        }}
      >
        {content}
      </aside>

      {/* Mobile overlay */}
      {open && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
            onClick={onToggle}
          />
          <aside
            className="fixed inset-y-0 left-0 z-50 w-72 md:hidden"
            style={{
              background: "var(--color-surface-raised)",
              borderRight: "1px solid var(--color-border-subtle)",
            }}
          >
            {content}
          </aside>
        </>
      )}
    </>
  );
}
