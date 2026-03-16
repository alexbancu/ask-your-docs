import { useState } from "react";
import { Routes, Route, Navigate, useParams } from "react-router-dom";
import ChatInterface from "./components/ChatInterface";
import DocumentSidebar from "./components/DocumentSidebar";
import DocumentViewer from "./components/DocumentViewer";
import Footer from "./components/Footer";
import { DemoProvider } from "./contexts/DemoContext";
import { useChatHistory } from "./hooks/useChatHistory";
import type { Message } from "./types";

function DemoShell() {
  const { demoSlug } = useParams<{ demoSlug: string }>();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const {
    conversations,
    activeId,
    saveConversation,
    loadConversation,
    deleteConversation,
    startNewChat,
  } = useChatHistory();

  const [conversationId, setConversationId] = useState<string>(crypto.randomUUID());

  const handleConversationUpdate = (msgs: Message[]) => {
    const firstUserMsg = msgs.find((m) => m.role === "user");
    if (!firstUserMsg) return;
    const title = firstUserMsg.content.slice(0, 50);
    saveConversation(conversationId, title, msgs);
  };

  const handleLoadConversation = (id: string) => {
    const msgs = loadConversation(id);
    setMessages(msgs);
    setConversationId(id);
    setSidebarOpen(false);
  };

  const handleNewChat = () => {
    startNewChat();
    setMessages([]);
    setConversationId(crypto.randomUUID());
    setSidebarOpen(false);
  };

  return (
    <DemoProvider value={{ demoSlug: demoSlug ?? "acme-corp" }}>
      <div className="flex h-dvh flex-col" style={{ background: "var(--color-surface)" }}>
        <div className="flex flex-1 overflow-hidden">
          <DocumentSidebar
            open={sidebarOpen}
            onToggle={() => setSidebarOpen(!sidebarOpen)}
            onNavigate={() => setSidebarOpen(false)}
            conversations={conversations}
            activeConversationId={activeId}
            onLoadConversation={handleLoadConversation}
            onDeleteConversation={deleteConversation}
            onNewChat={handleNewChat}
          />
          <main className="flex flex-1 flex-col overflow-hidden">
            <Routes>
              <Route
                path="/"
                element={
                  <ChatInterface
                    onOpenSidebar={() => setSidebarOpen(true)}
                    messages={messages}
                    setMessages={setMessages}
                    onConversationUpdate={handleConversationUpdate}
                  />
                }
              />
              <Route path="/documents/:slug" element={<DocumentViewer />} />
            </Routes>
          </main>
        </div>
        <Footer />
      </div>
    </DemoProvider>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/demo/:demoSlug/*" element={<DemoShell />} />
      <Route path="/" element={<Navigate to="/demo/acme-corp" replace />} />
      {/* Legacy routes redirect to default demo */}
      <Route path="/documents/:slug" element={<Navigate to="/demo/acme-corp" replace />} />
      <Route path="*" element={<Navigate to="/demo/acme-corp" replace />} />
    </Routes>
  );
}
