import { useEffect, useState } from "react";
import { Link, useParams, useLocation } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import type { DocumentContent } from "../types";
import { getDocumentContent } from "../api/client";
import { useDemo } from "../contexts/DemoContext";
import { TYPE_STYLES, DEFAULT_STYLE } from "../constants/styles";

export default function DocumentViewer() {
  const { slug } = useParams<{ slug: string }>();
  const { demoSlug } = useDemo();
  const location = useLocation();
  const [doc, setDoc] = useState<DocumentContent | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    setError(false);
    getDocumentContent(demoSlug, slug)
      .then(setDoc)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [demoSlug, slug]);

  // Scroll to section when hash changes (retry until ReactMarkdown renders the element)
  useEffect(() => {
    if (!location.hash || loading) return;
    const id = location.hash.slice(1);
    let attempts = 0;
    const maxAttempts = 10;

    const tryScroll = () => {
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: "smooth" });
        el.classList.add("section-highlight");
        setTimeout(() => el.classList.remove("section-highlight"), 2000);
        return;
      }
      attempts++;
      if (attempts < maxAttempts) {
        timer = setTimeout(tryScroll, 50);
      }
    };

    let timer = setTimeout(tryScroll, 50);
    return () => clearTimeout(timer);
  }, [location.hash, loading]);

  const basePath = `/demo/${demoSlug}`;

  if (loading) {
    return (
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header basePath={basePath} />
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[720px] px-4 py-8 md:px-6">
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-6 rounded animate-shimmer" style={{ width: `${70 + i * 5}%` }} />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header basePath={basePath} />
        <div className="flex flex-1 items-center justify-center">
          <div className="text-center">
            <p className="text-lg font-medium" style={{ color: "var(--color-text-primary)" }}>
              Document not found
            </p>
            <p className="mt-1 text-sm" style={{ color: "var(--color-text-secondary)" }}>
              The document you're looking for doesn't exist.
            </p>
            <Link
              to={basePath}
              className="mt-4 inline-block rounded-lg px-4 py-2 text-sm font-medium"
              style={{ background: "var(--color-accent)", color: "#fff" }}
            >
              Back to Chat
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const style = TYPE_STYLES[doc.document_type] ?? DEFAULT_STYLE;

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <Header basePath={basePath} title={doc.name} />
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[720px] px-4 py-6 md:px-6">
          {/* Metadata bar */}
          <div className="mb-6 flex flex-wrap items-center gap-3 text-[13px]">
            <span
              className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-medium"
              style={{ background: style.bg, color: style.text }}
            >
              {style.icon} {doc.document_type}
            </span>
            {doc.owner && (
              <span style={{ color: "var(--color-text-secondary)" }}>
                Owned by {doc.owner}
              </span>
            )}
            {doc.last_updated && (
              <span className="inline-flex items-center gap-1.5">
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ background: doc.is_stale ? "var(--color-orange-text)" : "#22C55E" }}
                />
                <span style={{ color: "var(--color-text-tertiary)" }}>
                  Updated {doc.last_updated}
                </span>
              </span>
            )}
            <span style={{ color: "var(--color-text-tertiary)" }}>
              {doc.section_count} section{doc.section_count !== 1 ? "s" : ""}
            </span>
          </div>

          {/* Markdown content */}
          <div className="prose prose-invert max-w-none">
            <ReactMarkdown
              components={{
                h2: ({ children, ...props }) => {
                  const text = String(children);
                  const match = text.match(/^(\d+)\./);
                  const id = match ? `section-${match[1]}` : undefined;
                  return <h2 id={id} {...props}>{children}</h2>;
                },
              }}
            >
              {doc.content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}

function Header({ basePath, title }: { basePath: string; title?: string }) {
  return (
    <header
      className="flex shrink-0 items-center gap-3 px-4 py-3 md:px-6"
      style={{ borderBottom: "1px solid var(--color-border-subtle)" }}
    >
      <Link
        to={basePath}
        className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-[13px] font-medium transition-colors"
        style={{ color: "var(--color-text-secondary)" }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-surface-overlay)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to Chat
      </Link>
      {title && (
        <span
          className="truncate text-[15px] font-semibold tracking-tight"
          style={{ color: "var(--color-text-primary)" }}
        >
          {title}
        </span>
      )}
    </header>
  );
}
