export interface DemoInfo {
  slug: string;
  name: string;
}

export interface DemosResponse {
  demos: DemoInfo[];
}

export interface Source {
  content: string;
  document_name: string;
  document_type: string;
  section_number: number;
}

export interface AskResponse {
  answer: string;
  sources: Source[];
  confidence: "high" | "low";
}

export interface DocumentInfo {
  name: string;
  document_type: string;
  page_count: number;
  slug: string;
  owner: string;
  last_updated: string | null;
  is_stale: boolean;
}

export interface DocumentContent {
  name: string;
  slug: string;
  document_type: string;
  content: string;
  owner: string;
  last_updated: string | null;
  is_stale: boolean;
  section_count: number;
}

export interface DocumentsResponse {
  documents: DocumentInfo[];
}

export interface HealthResponse {
  status: string;
  pinecone_connected: boolean;
  documents_indexed: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  confidence?: "high" | "low";
  isStreaming?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  updatedAt: number;
}
