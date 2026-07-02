"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Trash2, Plus, Database } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { listConnections, createConnection, deleteConnection, type Connection } from "@/lib/api";

export default function ConnectionsPage() {
  const { getToken } = useAuth();
  const [connections, setConnections] = useState<Connection[]>([]);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const token = await getToken();
    if (!token) return;
    setConnections(await listConnections(token));
  }

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      await createConnection(token, name.trim(), url.trim());
      setName("");
      setUrl("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add connection");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    const token = await getToken();
    if (!token) return;
    await deleteConnection(token, id);
    await load();
  }

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-xl font-semibold mb-1">Database Connections</h1>
      <p className="text-sm text-muted-foreground mb-8">
        Connect your own Postgres database. Credentials are encrypted at rest.
        If no connection is configured, the built-in demo dataset is used.
      </p>

      {connections.length > 0 && (
        <div className="space-y-3 mb-8">
          {connections.map((c) => (
            <Card key={c.id} className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <Database className="w-4 h-4 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">{c.name}</p>
                  <p className="text-xs text-muted-foreground">Added {new Date(c.created_at).toLocaleDateString()}</p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={() => handleDelete(c.id)}>
                <Trash2 className="w-4 h-4 text-destructive" />
              </Button>
            </Card>
          ))}
        </div>
      )}

      <Card className="p-5">
        <h2 className="text-sm font-medium mb-4 flex items-center gap-2">
          <Plus className="w-4 h-4" /> Add connection
        </h2>
        <form onSubmit={handleAdd} className="space-y-3">
          <Input
            placeholder="Connection name (e.g. Production DB)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <Input
            placeholder="postgresql+psycopg2://user:pass@host:5432/dbname"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" disabled={loading || !name.trim() || !url.trim()}>
            {loading ? "Adding…" : "Add connection"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
