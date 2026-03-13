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
}
