import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { BarChart2, Database, MessageSquare } from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Chat", icon: MessageSquare },
  { href: "/settings/connections", label: "Connections", icon: Database },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-56 border-r flex flex-col shrink-0">
        <div className="px-4 py-5 border-b flex items-center gap-2">
          <BarChart2 className="w-5 h-5 text-primary" />
          <span className="font-semibold text-sm">SQL Copilot</span>
        </div>
        <nav className="flex-1 px-2 py-4 space-y-1">
          {navItems.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="px-4 py-4 border-t">
          <UserButton />
        </div>
      </aside>
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
