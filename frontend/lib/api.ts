const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type StreamEvent =
  | { type: "tool_call"; tool: string; input: Record<string, unknown> }
  | { type: "tool_result"; tool: string; result: Record<string, unknown> }
  | { type: "answer"; answer: string; sql: string | null; columns: string[] | null; rows: unknown[][] | null; truncated: boolean }
  | { type: "limit_exceeded"; message: string }
  | { type: "conversation"; conversation_id: string };

export type Connection = { id: string; name: string; created_at: string };

export type BillingStatus = {
  tier: "free" | "pro";
  subscription_status: string | null;
  usage_this_month: number;
  monthly_limit: number | null;
};

export async function* streamChat(
  question: string,
  token: string,
  conversationId?: string
): AsyncGenerator<StreamEvent> {
  const params = new URLSearchParams({ question });
  if (conversationId) params.set("conversation_id", conversationId);

  const res = await fetch(`${API_URL}/chat/stream?${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) throw new Error(`API error ${res.status}`);

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6).trim();
      if (data === "[DONE]") return;
      try {
        yield JSON.parse(data) as StreamEvent;
      } catch {
        // malformed event — skip
      }
    }
  }
}

export async function listConnections(token: string): Promise<Connection[]> {
  const res = await fetch(`${API_URL}/connections`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function createConnection(
  token: string,
  name: string,
  database_url: string
): Promise<Connection> {
  const res = await fetch(`${API_URL}/connections`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ name, database_url }),
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function deleteConnection(token: string, id: string): Promise<void> {
  const res = await fetch(`${API_URL}/connections/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
}

export async function getBillingStatus(token: string): Promise<BillingStatus> {
  const res = await fetch(`${API_URL}/billing/status`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function createCheckoutSession(token: string): Promise<{ url: string }> {
  const res = await fetch(`${API_URL}/billing/checkout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function createPortalSession(token: string): Promise<{ url: string }> {
  const res = await fetch(`${API_URL}/billing/portal`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}
