import { type ReactNode, useMemo } from "react";
import Markdown, { type Components } from "react-markdown";
import { Link } from "react-router-dom";
import type { Message, Source } from "../types";
import { nameToSlug } from "../constants/styles";
import SourcePanel from "./SourcePanel";

type SourceMap = Map<string, { slug: string; section_number: number }>;

function buildSourceMap(sources: Source[]): SourceMap {
  const map: SourceMap = new Map();
  for (const s of sources) {
    if (!map.has(s.document_name)) {
      map.set(s.document_name, {
        slug: nameToSlug(s.document_name),
        section_number: s.section_number,
      });
    }
  }
  return map;
}

function linkifyDocumentNames(text: string, sourceMap: SourceMap): ReactNode[] {
  if (sourceMap.size === 0) return [text];

  // Sort names longest-first so "Employee Handbook" matches before "Employee"
  const names = Array.from(sourceMap.keys()).sort((a, b) => b.length - a.length);
  const escaped = names.map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escaped.join("|")})`, "g");

  const parts = text.split(pattern);
  return parts.map((part, i) => {
    const entry = sourceMap.get(part);
    if (entry) {
      const hash = entry.section_number > 0 ? `#section-${entry.section_number}` : "";
      return (
        <Link key={i} to={`/documents/${entry.slug}${hash}`} className="doc-inline-link">
          {part}
        </Link>
      );
    }
    return part;
  });
}

interface MessageBubbleProps {
  message: Message;
  index: number;
}

export default function MessageBubble({ message, index }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div
        className="flex justify-end animate-fade-in-up"
        style={{ animationDelay: `${index * 50}ms` }}
      >
        <div
          className="max-w-[75%] rounded-2xl rounded-br-md px-4 py-2.5"
          style={{
            background: "var(--color-user-bubble)",
            color: "var(--color-user-bubble-text)",
          }}
        >
          <p className="text-[15px] leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  const sourceMap = useMemo(
    () => buildSourceMap(message.sources ?? []),
    [message.sources],
  );

  const markdownComponents = useMemo<Components>(() => {
    if (sourceMap.size === 0) return {};
    return {
      p({ children }) {
        return (
          <p>
            {Array.isArray(children)
              ? children.flatMap((child) =>
                  typeof child === "string" ? linkifyDocumentNames(child, sourceMap) : child,
                )
              : typeof children === "string"
                ? linkifyDocumentNames(children, sourceMap)
                : children}
          </p>
        );
      },
      li({ children }) {
        return (
          <li>
            {Array.isArray(children)
              ? children.flatMap((child) =>
                  typeof child === "string" ? linkifyDocumentNames(child, sourceMap) : child,
                )
              : typeof children === "string"
                ? linkifyDocumentNames(children, sourceMap)
                : children}
          </li>
        );
      },
    };
  }, [sourceMap]);

  const showThinking = message.isStreaming && !message.content && !message.sources;

  return (
    <div
      className="animate-fade-in-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* Thinking indicator — before sources arrive */}
      {showThinking && (
        <div className="mb-3">
          <p
            className="mb-2 text-[11px] font-medium uppercase tracking-wider"
            style={{ color: "var(--color-text-tertiary)" }}
          >
            Searching documents...
          </p>
          <div className="space-y-2">
            <div className="h-4 w-3/4 rounded animate-shimmer" />
            <div className="h-4 w-1/2 rounded animate-shimmer" />
            <div className="h-4 w-2/3 rounded animate-shimmer" />
          </div>
        </div>
      )}

      {/* Source cards — Perplexity style, above the answer */}
      {message.sources && message.sources.length > 0 && (
        <div className="mb-3">
          <p
            className="mb-2 text-[11px] font-medium uppercase tracking-wider"
            style={{ color: "var(--color-text-tertiary)" }}
          >
            Sources
          </p>
          <SourcePanel sources={message.sources} />
        </div>
      )}

      {/* Answer block */}
      {(message.content || !showThinking) && (
        <div
          className="rounded-xl px-5 py-4"
          style={{
            background: "var(--color-surface-raised)",
            border: "1px solid var(--color-border-subtle)",
          }}
        >
          <div
            className={`prose prose-invert prose-sm max-w-none
              prose-headings:font-semibold prose-headings:tracking-tight
              prose-h2:text-base prose-h3:text-sm
              prose-p:leading-relaxed prose-p:text-[15px]
              prose-li:text-[15px] prose-li:leading-relaxed
              prose-strong:font-semibold
              prose-a:no-underline hover:prose-a:underline
              [&>*:first-child]:mt-0 [&>*:last-child]:mb-0${message.isStreaming && message.content ? " streaming-cursor" : ""}`}
            style={{ color: "var(--color-text-primary)" }}
          >
            <Markdown components={markdownComponents}>{message.content}</Markdown>
          </div>
        </div>
      )}
    </div>
  );
}
