import { useState } from "react";
import { Routes, Route } from "react-router-dom";
import ChatInterface from "./components/ChatInterface";
import DocumentSidebar from "./components/DocumentSidebar";
import DocumentViewer from "./components/DocumentViewer";
import Footer from "./components/Footer";
import { useChatHistory } from "./hooks/useChatHistory";
import type { Message } from "./types";

export default function App() {
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
  );
}
