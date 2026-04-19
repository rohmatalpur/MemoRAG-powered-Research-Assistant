export interface Paper {
  paper_id: string;
  session_id: string;
  title: string;
  authors: string;
  year: number | null;
  status: "processing" | "indexed" | "error";
  file_path: string;
  concept_tags: string[];
  created_at: string;
  memory_digest?: string;
}

export interface Session {
  session_id: string;
  created_at: string;
  paper_count: number;
  new_concepts: number;
  new_edges: number;
  new_clusters: number;
  papers?: Paper[];
}

export interface GraphNode {
  id: string;
  type: "paper" | "concept" | "cluster";
  label: string;
  year?: number;
  session_added?: string;
  pagerank_score?: number;
  paper_count?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  rel: string;
  similarity?: number;
  on_concept?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Citation {
  ref_id: number;
  paper: string;
  section: string;
  page: number;
  quote: string;
  deep_link: string;
}

export interface MemoryClue {
  text: string;
  mentioned_papers: string[];
  suggested_terms: string[];
  confidence: number;
}

export interface ChatResponse {
  intent: string;
  draft_mode: boolean;
  clue: MemoryClue;
  answer: string;
  citations: Citation[];
  memory_trace: string[];
  outline?: {
    sections: {
      title: string;
      theme: string;
      papers: string[];
      sub_points: string[];
    }[];
  };
}

export interface Cluster {
  cluster_id: string | number;
  label: string;
  paper_count: number;
  members: string[];
}

export interface Annotation {
  id: number;
  text: string;
  page: number;
  created_at: string;
}
