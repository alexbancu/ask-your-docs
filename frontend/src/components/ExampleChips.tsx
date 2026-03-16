interface ExampleChipsProps {
  onSelect: (question: string) => void;
}

const EXAMPLES = [
  {
    icon: "📋",
    label: "PTO & Benefits",
    question: "What is the PTO policy and how does the 401k match work?",
  },
  {
    icon: "🚨",
    label: "Incident Response",
    question: "How do I handle a P1 incident and what are the SLOs?",
  },
  {
    icon: "🔐",
    label: "Security Standards",
    question: "What encryption standards and compliance certifications does Acme have?",
  },
  {
    icon: "🚀",
    label: "New Hire Setup",
    question: "What are the 30/60/90 day expectations for new engineers?",
  },
];

export default function ExampleChips({ onSelect }: ExampleChipsProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {EXAMPLES.map((ex) => (
        <button
          key={ex.label}
          onClick={() => onSelect(ex.question)}
          className="group flex items-start gap-3 rounded-xl p-4 text-left transition-all duration-200"
          style={{
            background: "var(--color-surface-raised)",
            border: "1px solid var(--color-border-subtle)",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--color-surface-overlay)";
            e.currentTarget.style.borderColor = "var(--color-border)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "var(--color-surface-raised)";
            e.currentTarget.style.borderColor = "var(--color-border-subtle)";
          }}
        >
          <span className="mt-0.5 text-lg leading-none">{ex.icon}</span>
          <div className="min-w-0">
            <p
              className="text-sm font-medium"
              style={{ color: "var(--color-text-primary)" }}
            >
              {ex.label}
            </p>
            <p
              className="mt-0.5 text-[13px] leading-snug"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {ex.question}
            </p>
          </div>
          <svg
            className="ml-auto mt-1 h-4 w-4 shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
            style={{ color: "var(--color-text-tertiary)" }}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4.5 19.5l15-15m0 0H8.25m11.25 0v11.25" />
          </svg>
        </button>
      ))}
    </div>
  );
}
