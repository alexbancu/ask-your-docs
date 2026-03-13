import { useState } from "react";
import ChatInterface from "./components/ChatInterface";
import DocumentSidebar from "./components/DocumentSidebar";
import Footer from "./components/Footer";

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      <div className="flex flex-1 overflow-hidden">
        <DocumentSidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <main className="flex flex-1 flex-col overflow-hidden">
          <ChatInterface />
        </main>
      </div>
      <Footer />
    </div>
  );
}
