import type { AskResponse, DocumentContent, DocumentsResponse, HealthResponse, Source } from "../types";

const API_URL = import.meta.env.VITE_API_URL ?? "/api";

export async function askQuestion(question: string): Promise<AskResponse> {
  const response = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    throw new Error(`Failed to ask question: ${response.status}`);
  }

  return response.json() as Promise<AskResponse>;
}

interface StreamCallbacks {
  onSources: (sources: Source[], confidence: "high" | "low") => void;
  onToken: (token: string) => void;
  onDone: () => void;
}

export async function askQuestionStream(
  question: string,
  callbacks: StreamCallbacks,
): Promise<void> {
  const response = await fetch(`${API_URL}/ask/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    throw new Error(`Failed to ask question: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7);
      } else if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (currentEvent === "sources") {
          const parsed = JSON.parse(data) as {
            sources: Source[];
            confidence: "high" | "low";
          };
          callbacks.onSources(parsed.sources, parsed.confidence);
        } else if (currentEvent === "token") {
          callbacks.onToken(JSON.parse(data) as string);
        } else if (currentEvent === "done") {
          callbacks.onDone();
        }
        currentEvent = "";
      }
    }
  }
}

export async function getDocuments(): Promise<DocumentsResponse> {
  const response = await fetch(`${API_URL}/documents`);

  if (!response.ok) {
    throw new Error(`Failed to fetch documents: ${response.status}`);
  }

  return response.json() as Promise<DocumentsResponse>;
}

export async function getDocumentContent(slug: string): Promise<DocumentContent> {
  const response = await fetch(`${API_URL}/documents/${slug}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch document: ${response.status}`);
  }

  return response.json() as Promise<DocumentContent>;
}

export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_URL}/health`);

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }

  return response.json() as Promise<HealthResponse>;
}
