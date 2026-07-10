"use client";

import { useRef, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MessageBubble, type Message } from "@/components/chat/MessageBubble";
import { streamChat } from "@/lib/api";

const TOOL_LABELS: Record<string, string> = {
  list_tables: "Fetching table list…",
  get_schema: "Reading schema…",
  run_sql: "Running SQL…",
};

export default function DashboardPage() {
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);

  const push = useCallback((msg: Message) => {
    setMessages((prev) => [...prev, msg]);
    scrollToBottom();
  }, []);

  const replaceLastStatus = useCallback((content: string) => {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last?.role === "status") return [...prev.slice(0, -1), { role: "status", content }];
      return [...prev, { role: "status", content }];
    });
    scrollToBottom();
  }, []);

  const removeLastStatus = useCallback(() => {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      return last?.role === "status" ? prev.slice(0, -1) : prev;
    });
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setLoading(true);
    push({ role: "user", content: question });

    try {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");

      replaceLastStatus("Thinking…");

      for await (const event of streamChat(question, token)) {
        if (event.type === "tool_call") {
          replaceLastStatus(TOOL_LABELS[event.tool] ?? `Calling ${event.tool}…`);
        } else if (event.type === "answer") {
          removeLastStatus();
          push({
            role: "assistant",
            content: event.answer,
            sql: event.sql,
            columns: event.columns ?? undefined,
            rows: event.rows ?? undefined,
            truncated: event.truncated,
          });
        } else if (event.type === "limit_exceeded") {
          removeLastStatus();
          push({ role: "assistant", content: event.message, limitExceeded: true });
        }
      }
    } catch (err) {
      removeLastStatus();
      push({ role: "assistant", content: `Something went wrong: ${err instanceof Error ? err.message : "unknown error"}`, failed: true });
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground gap-3">
            <p className="text-lg font-medium">Ask your database anything.</p>
            <p className="text-sm">Try: <em>&quot;What is our total active MRR broken down by plan?&quot;</em></p>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t px-6 py-4">
        <form onSubmit={handleSubmit} className="flex gap-3 items-end">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your data… (Enter to send, Shift+Enter for newline)"
            className="resize-none min-h-[44px] max-h-40"
            rows={1}
            disabled={loading}
          />
          <Button type="submit" disabled={loading || !input.trim()} size="icon" className="shrink-0">
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
