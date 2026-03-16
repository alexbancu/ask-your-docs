export default function Footer() {
  return (
    <footer
      className="shrink-0 px-4 py-2.5 text-center text-[11px]"
      style={{
        color: "var(--color-text-tertiary)",
        borderTop: "1px solid var(--color-border-subtle)",
      }}
    >
      Built by{" "}
      <a
        href="https://github.com/alexbancu"
        target="_blank"
        rel="noopener noreferrer"
        className="transition-colors duration-150"
        style={{ color: "var(--color-text-secondary)" }}
        onMouseEnter={(e) => (e.currentTarget.style.color = "var(--color-accent)")}
        onMouseLeave={(e) => (e.currentTarget.style.color = "var(--color-text-secondary)")}
      >
        Alex Bancu
      </a>
      <span className="mx-1.5" style={{ color: "var(--color-border)" }}>·</span>
      Gemini + Pinecone + LangChain
    </footer>
  );
}
