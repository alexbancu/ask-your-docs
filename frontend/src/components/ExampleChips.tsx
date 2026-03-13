interface ExampleChipsProps {
  onSelect: (question: string) => void;
}

const EXAMPLES = [
  "What is the PTO policy?",
  "How do I handle a P1 incident?",
  "What equipment stipend do new hires get?",
  "What encryption standards does Acme use?",
  "What is the API rate limit?",
  "What are the 30/60/90 day expectations?",
];

export default function ExampleChips({ onSelect }: ExampleChipsProps) {
  return (
    <div className="flex flex-wrap justify-center gap-2 px-4">
      {EXAMPLES.map((q) => (
        <button
          key={q}
          onClick={() => onSelect(q)}
          className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
        >
          {q}
        </button>
      ))}
    </div>
  );
}
