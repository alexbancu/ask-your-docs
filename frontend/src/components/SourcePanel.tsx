import { useState } from "react";
import type { Source } from "../types";

interface SourcePanelProps {
  sources: Source[];
}

const TYPE_COLORS: Record<string, string> = {
  hr: "bg-green-100 text-green-700",
  engineering: "bg-blue-100 text-blue-700",
  onboarding: "bg-purple-100 text-purple-700",
  product: "bg-orange-100 text-orange-700",
  security: "bg-red-100 text-red-700",
};

export default function SourcePanel({ sources }: SourcePanelProps) {
  const [expanded, setExpanded] = useState(false);

  if (sources.length === 0) return null;

  // Group sources by document name
  const grouped = sources.reduce<Record<string, Source[]>>((acc, source) => {
    const key = source.document_name;
    if (!acc[key]) acc[key] = [];
    acc[key].push(source);
    return acc;
  }, {});

  return (
    <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-slate-500 hover:text-slate-700"
      >
        <span>{sources.length} source{sources.length !== 1 ? "s" : ""}</span>
        <span>{expanded ? "Hide" : "Show"}</span>
      </button>

      {expanded && (
        <div className="border-t border-slate-200 px-3 py-2 space-y-3">
          {Object.entries(grouped).map(([docName, docSources]) => (
            <div key={docName}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold text-slate-700">{docName}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                    TYPE_COLORS[docSources[0].document_type] ?? "bg-gray-100 text-gray-700"
                  }`}
                >
                  {docSources[0].document_type}
                </span>
              </div>
              {docSources.map((source, i) => (
                <div key={i} className="ml-2 mb-1 text-xs text-slate-500">
                  <span className="text-slate-400">Section {source.section_number}:</span>{" "}
                  {source.content}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
