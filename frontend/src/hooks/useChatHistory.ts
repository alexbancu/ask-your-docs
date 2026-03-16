import { useCallback, useState } from "react";
import type { Conversation, Message } from "../types";

const STORAGE_KEY = "chat-history";

function readStorage(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Conversation[]) : [];
  } catch {
    return [];
  }
}

function writeStorage(conversations: Conversation[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
}

export function useChatHistory() {
  const [conversations, setConversations] = useState<Conversation[]>(() =>
    readStorage().sort((a, b) => b.updatedAt - a.updatedAt),
  );
  const [activeId, setActiveId] = useState<string | null>(null);

  const saveConversation = useCallback(
    (id: string, title: string, messages: Message[]) => {
      setConversations((prev) => {
        const existing = prev.find((c) => c.id === id);
        let next: Conversation[];
        if (existing) {
          next = prev.map((c) =>
            c.id === id ? { ...c, title, messages, updatedAt: Date.now() } : c,
          );
        } else {
          next = [{ id, title, messages, updatedAt: Date.now() }, ...prev];
        }
        next.sort((a, b) => b.updatedAt - a.updatedAt);
        writeStorage(next);
        return next;
      });
    },
    [],
  );

  const loadConversation = useCallback(
    (id: string): Message[] => {
      setActiveId(id);
      const convo = readStorage().find((c) => c.id === id);
      return convo ? convo.messages : [];
    },
    [],
  );

  const deleteConversation = useCallback(
    (id: string) => {
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== id);
        writeStorage(next);
        return next;
      });
      setActiveId((prev) => (prev === id ? null : prev));
    },
    [],
  );

  const startNewChat = useCallback(() => {
    setActiveId(null);
  }, []);

  return {
    conversations,
    activeId,
    saveConversation,
    loadConversation,
    deleteConversation,
    startNewChat,
  };
}
