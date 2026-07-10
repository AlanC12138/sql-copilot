import Link from "next/link";
import { auth } from "@clerk/nextjs/server";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const features = [
  { title: "Natural language → SQL", body: "Ask questions in plain English. The agent writes and runs the SQL for you." },
  { title: "Read-only safety sandbox", body: "Structural validation, forbidden-keyword scan, EXPLAIN cost guard, and a read-only DB role." },
  { title: "86% benchmark accuracy", body: "Measured against a 50-question NL→SQL eval suite. Scores are tracked on every prompt change." },
  { title: "Multi-tenant & secure", body: "Organizations, per-tenant DB connections, and credentials encrypted at rest with Fernet." },
];

export default async function LandingPage() {
  const { userId } = await auth();

  return (
    <div className="flex flex-col min-h-screen">
      <header className="border-b px-6 py-4 flex items-center justify-between">
        <span className="font-semibold text-lg tracking-tight">SQL Copilot</span>
        <div className="flex gap-3">
          {userId ? (
            <Link href="/dashboard" className={cn(buttonVariants())}>Go to app →</Link>
          ) : (
            <>
              <Link href="/sign-in" className={cn(buttonVariants({ variant: "ghost" }))}>Sign in</Link>
              <Link href="/sign-up" className={cn(buttonVariants())}>Get started</Link>
            </>
          )}
        </div>
      </header>

      <main className="flex-1">
        <section className="px-6 py-24 text-center max-w-3xl mx-auto">
          <h1 className="text-5xl font-bold tracking-tight mb-6">
            Ask your database<br />anything in plain English.
          </h1>
          <p className="text-xl text-muted-foreground mb-10">
            SQL Copilot translates natural language questions into verified SQL, runs them
            safely against your database, and returns results as tables and charts — in seconds.
          </p>
          <div className="flex gap-4 justify-center">
            {userId ? (
              <Link href="/dashboard" className={cn(buttonVariants({ size: "lg" }))}>Open dashboard →</Link>
            ) : (
              <>
                <Link href="/sign-up" className={cn(buttonVariants({ size: "lg" }))}>Start for free</Link>
                <Link href="/sign-in" className={cn(buttonVariants({ size: "lg", variant: "outline" }))}>Sign in</Link>
              </>
            )}
          </div>
        </section>

        <section className="px-6 py-12 bg-muted/40">
          <div className="max-w-3xl mx-auto">
            <p className="text-sm text-muted-foreground text-center mb-6 uppercase tracking-wider">Try asking</p>
            <div className="grid gap-3">
              {[
                "What is our total active MRR broken down by plan?",
                "Which customers on the pro plan have raised a support ticket?",
                "What percentage of invoices failed last year?",
                "Show me the customer with the highest total paid invoice amount.",
              ].map((q) => (
                <div key={q} className="bg-background border rounded-lg px-5 py-3 text-sm font-mono text-muted-foreground">
                  {q}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="px-6 py-20 max-w-5xl mx-auto">
          <div className="grid md:grid-cols-2 gap-8">
            {features.map((f) => (
              <div key={f.title} className="border rounded-xl p-6">
                <h3 className="font-semibold mb-2">{f.title}</h3>
                <p className="text-sm text-muted-foreground">{f.body}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t px-6 py-6 text-center text-sm text-muted-foreground">
        SQL Copilot — built by Alan Chen
      </footer>
    </div>
  );
}
