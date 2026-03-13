import type { AskResponse, DocumentsResponse, HealthResponse } from "../types";

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

export async function getDocuments(): Promise<DocumentsResponse> {
  const response = await fetch(`${API_URL}/documents`);

  if (!response.ok) {
    throw new Error(`Failed to fetch documents: ${response.status}`);
  }

  return response.json() as Promise<DocumentsResponse>;
}

export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_URL}/health`);

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }

  return response.json() as Promise<HealthResponse>;
}
