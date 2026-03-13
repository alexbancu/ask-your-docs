export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white px-4 py-3 text-center text-xs text-slate-400">
      Built by{" "}
      <a
        href="https://github.com/alexbancu"
        target="_blank"
        rel="noopener noreferrer"
        className="text-indigo-500 hover:text-indigo-600"
      >
        Alex Bancu
      </a>
      {" "}| Powered by Gemini + Pinecone + LangChain
    </footer>
  );
}
