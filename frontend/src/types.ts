export type BenchmarkMeta = {
  slug: string;
  name: string;
  description: string;
};

export type BenchmarkResult = {
  benchmark: string;
  started_at: string;
  finished_at: string;
  prompt: string;
  response: string;
  expected: string | null;
  score: number;
  duration_ms: number;
  ttft_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  metadata: Record<string, unknown>;
  run_id: string;
};

export type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
};
