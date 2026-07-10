"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronRight, AlertCircle, Sparkles, Bot, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ResultTable } from "./ResultTable";
import { ResultChart } from "./ResultChart";

export type Message =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; sql?: string | null; columns?: string[] | null; rows?: unknown[][] | null; truncated?: boolean; failed?: boolean; limitExceeded?: boolean }
  | { role: "status"; content: string };

export function MessageBubble({ message }: { message: Message }) {
  const [sqlOpen, setSqlOpen] = useState(false);

  if (message.role === "status") {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-1 pl-1">
        <span className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
        {message.content}
      </div>
    );
  }

  if (message.role === "user") {
    return (
      <div className="flex gap-3 justify-end">
        <div className="max-w-[80%] bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-3 text-sm">
          {message.content}
        </div>
        <div className="shrink-0 w-7 h-7 rounded-full bg-muted flex items-center justify-center mt-1">
          <User className="w-4 h-4" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="shrink-0 w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center mt-1">
        <Bot className="w-4 h-4 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        {message.failed && (
          <div className="flex items-center gap-2 text-destructive text-sm mb-2">
            <AlertCircle className="w-4 h-4" />
            <span>Agent could not complete the query.</span>
          </div>
        )}
        {message.limitExceeded && (
          <div className="flex items-center gap-2 text-primary text-sm mb-2">
            <Sparkles className="w-4 h-4" />
            <span>Free tier limit reached</span>
          </div>
        )}
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        {message.limitExceeded && (
          <Link href="/settings/billing" className="text-sm text-primary underline underline-offset-2 mt-1 inline-block">
            Upgrade to Pro →
          </Link>
        )}

        {message.sql && (
          <div className="mt-3">
            <button
              onClick={() => setSqlOpen((v) => !v)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {sqlOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              View SQL
            </button>
            {sqlOpen && (
              <pre className="mt-2 p-3 bg-muted rounded-lg text-xs overflow-x-auto font-mono">
                {message.sql}
              </pre>
            )}
          </div>
        )}

        {message.columns && message.rows && (
          <>
            <div className="flex items-center gap-2 mt-3 mb-1">
              <Badge variant="secondary" className="text-xs">{message.rows.length} row{message.rows.length !== 1 ? "s" : ""}</Badge>
            </div>
            <ResultTable columns={message.columns} rows={message.rows} truncated={message.truncated ?? false} />
            <ResultChart columns={message.columns} rows={message.rows} />
          </>
        )}
      </div>
    </div>
  );
}
