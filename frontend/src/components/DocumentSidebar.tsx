import { useEffect, useState } from "react";
import type { DocumentInfo } from "../types";
import { getDocuments } from "../api/client";

const TYPE_COLORS: Record<string, string> = {
  hr: "bg-green-100 text-green-700",
  engineering: "bg-blue-100 text-blue-700",
  onboarding: "bg-purple-100 text-purple-700",
  product: "bg-orange-100 text-orange-700",
  security: "bg-red-100 text-red-700",
};

interface DocumentSidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export default function DocumentSidebar({ collapsed, onToggle }: DocumentSidebarProps) {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    getDocuments()
      .then((res) => setDocuments(res.documents))
      .catch(() => setError(true));
  }, []);

  // Group documents by type
  const grouped = documents.reduce<Record<string, DocumentInfo[]>>((acc, doc) => {
    if (!acc[doc.document_type]) acc[doc.document_type] = [];
    acc[doc.document_type].push(doc);
    return acc;
  }, {});

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={onToggle}
        className="fixed top-4 left-4 z-50 rounded-lg border border-slate-200 bg-white p-2 shadow-sm md:hidden"
        aria-label="Toggle sidebar"
      >
        <svg className="h-5 w-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 transform border-r border-slate-200 bg-white transition-transform md:static md:translate-x-0 ${
          collapsed ? "-translate-x-full" : "translate-x-0"
        }`}
      >
        <div className="flex h-full flex-col p-4">
          <h3 className="mb-4 text-sm font-semibold text-slate-800">Knowledge Base</h3>

          {error ? (
            <p className="text-xs text-red-500">Failed to load documents</p>
          ) : documents.length === 0 ? (
            <p className="text-xs text-slate-400">Loading...</p>
          ) : (
            <div className="space-y-4">
              {Object.entries(grouped).map(([type, docs]) => (
                <div key={type}>
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium mb-2 ${
                      TYPE_COLORS[type] ?? "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {type}
                  </span>
                  {docs.map((doc) => (
                    <div key={doc.name} className="ml-1 mb-1">
                      <p className="text-xs font-medium text-slate-700">{doc.name}</p>
                      <p className="text-[10px] text-slate-400">
                        {doc.page_count} section{doc.page_count !== 1 ? "s" : ""}
                      </p>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>

      {/* Overlay for mobile */}
      {!collapsed && (
        <div
          className="fixed inset-0 z-30 bg-black/20 md:hidden"
          onClick={onToggle}
        />
      )}
    </>
  );
}
