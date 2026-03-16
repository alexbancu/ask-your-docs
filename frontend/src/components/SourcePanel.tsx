import { Link } from "react-router-dom";
import type { Source } from "../types";
import { TYPE_STYLES, DEFAULT_STYLE, nameToSlug } from "../constants/styles";

interface SourcePanelProps {
  sources: Source[];
}

export default function SourcePanel({ sources }: SourcePanelProps) {
  if (sources.length === 0) return null;

  // Deduplicate by document name + section so each unique section gets a card
  const seen = new Map<string, Source>();
  for (const source of sources) {
    const key = `${source.document_name}::${source.section_number}`;
    if (!seen.has(key)) {
      seen.set(key, source);
    }
  }
  const unique = Array.from(seen.values());

  return (
    <div className="flex gap-2 overflow-x-auto pb-1 mb-1" style={{ scrollbarWidth: "none" }}>
      {unique.map((source, i) => {
        const style = TYPE_STYLES[source.document_type] ?? DEFAULT_STYLE;
        const slug = nameToSlug(source.document_name);
        const hash = source.section_number > 0 ? `#section-${source.section_number}` : "";
        return (
          <Link
            key={`${source.document_name}-${i}`}
            to={`/documents/${slug}${hash}`}
            className="flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 transition-colors duration-150"
            style={{
              background: style.bg,
              border: `1px solid color-mix(in srgb, ${style.text} 20%, transparent)`,
              textDecoration: "none",
            }}
          >
            <span className="text-sm leading-none">{style.icon}</span>
            <div className="min-w-0">
              <p className="text-[12px] font-medium truncate" style={{ color: style.text }}>
                {source.document_name}
              </p>
              {source.section_number > 0 && (
                <p className="text-[10px] mt-0.5" style={{ color: "var(--color-text-tertiary)" }}>
                  Section {source.section_number}
                </p>
              )}
            </div>
          </Link>
        );
      })}
    </div>
  );
}
