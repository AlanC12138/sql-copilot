"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders the agent's reply.
 *
 * The model writes markdown — bold, bullets, GFM tables, fenced code — and this
 * used to go into a plain <p> with whitespace-pre-wrap, so every asterisk and
 * pipe showed up literally.
 *
 * Raw HTML is deliberately not enabled. react-markdown ignores embedded HTML
 * unless rehype-raw is added, and the text being rendered is model output
 * derived from database contents, so it is exactly the input you would not want
 * interpreted as markup.
 *
 * Styling is explicit per element rather than a typography plugin: it is a
 * handful of rules, and they have to line up with the surrounding chat bubble
 * rather than with prose defaults.
 */
const components: Components = {
  p: ({ children }) => <p className="text-sm leading-relaxed mb-2 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,

  ul: ({ children }) => <ul className="text-sm leading-relaxed list-disc pl-5 mb-2 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="text-sm leading-relaxed list-decimal pl-5 mb-2 space-y-1">{children}</ol>,
  li: ({ children }) => <li className="marker:text-muted-foreground">{children}</li>,

  h1: ({ children }) => <h1 className="text-base font-semibold mt-3 mb-1.5 first:mt-0">{children}</h1>,
  h2: ({ children }) => <h2 className="text-sm font-semibold mt-3 mb-1.5 first:mt-0">{children}</h2>,
  h3: ({ children }) => <h3 className="text-sm font-semibold mt-3 mb-1.5 first:mt-0">{children}</h3>,

  a: ({ href, children }) => (
    // Model-authored links point wherever the model decided; noopener/noreferrer
    // and an explicit new tab keep that away from this origin's context.
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer nofollow"
      className="text-primary underline underline-offset-2"
    >
      {children}
    </a>
  ),

  // A fenced block arrives as <pre><code>. Styling <pre> alone would leave the
  // inner <code> with inline-code styling on top of it, hence both.
  pre: ({ children }) => (
    <pre className="mt-2 mb-2 p-3 bg-muted rounded-lg text-xs overflow-x-auto font-mono">{children}</pre>
  ),
  code: ({ className, children }) => {
    const fenced = typeof className === "string" && className.startsWith("language-");
    if (fenced) return <code className="font-mono">{children}</code>;
    return <code className="px-1 py-0.5 rounded bg-muted font-mono text-[0.85em]">{children}</code>;
  },

  // GFM tables. The wrapper scrolls instead of forcing the chat column wider.
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
  th: ({ children }) => (
    <th className="text-left font-medium px-3 py-2 border-b border-border whitespace-nowrap">{children}</th>
  ),
  td: ({ children }) => <td className="px-3 py-2 border-b border-border last:border-0">{children}</td>,

  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-border pl-3 text-muted-foreground my-2">{children}</blockquote>
  ),
  hr: () => <hr className="my-3 border-border" />,
};

export function Markdown({ children }: { children: string }) {
  return (
    <div className="min-w-0">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
