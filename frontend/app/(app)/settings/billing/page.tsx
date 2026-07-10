"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { CreditCard, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getBillingStatus, createCheckoutSession, createPortalSession, type BillingStatus } from "@/lib/api";

export default function BillingPage() {
  const { getToken } = useAuth();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const token = await getToken();
    if (!token) return;
    setStatus(await getBillingStatus(token));
  }

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleUpgrade() {
    setError(null);
    setLoading(true);
    try {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      const { url } = await createCheckoutSession(token);
      window.location.href = url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start checkout");
      setLoading(false);
    }
  }

  async function handleManage() {
    setError(null);
    setLoading(true);
    try {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      const { url } = await createPortalSession(token);
      window.location.href = url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open billing portal");
      setLoading(false);
    }
  }

  const justSucceeded = searchParams.get("success") === "true";
  const justCanceled = searchParams.get("canceled") === "true";
  const usagePct = status?.monthly_limit
    ? Math.min(100, Math.round((status.usage_this_month / status.monthly_limit) * 100))
    : 0;

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-xl font-semibold mb-1">Billing</h1>
      <p className="text-sm text-muted-foreground mb-8">
        Manage your plan and see how many questions you&apos;ve asked this month.
      </p>

      {justSucceeded && (
        <p className="text-sm text-green-600 mb-4">
          You&apos;re on Pro now — thanks for upgrading! It may take a few seconds to reflect below.
        </p>
      )}
      {justCanceled && (
        <p className="text-sm text-muted-foreground mb-4">Checkout was canceled — no changes were made.</p>
      )}

      {status && (
        <Card className="p-5 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              {status.tier === "pro" ? (
                <Sparkles className="w-4 h-4 text-primary" />
              ) : (
                <CreditCard className="w-4 h-4 text-muted-foreground" />
              )}
              <span className="text-sm font-medium">
                {status.tier === "pro" ? "Pro plan" : "Free plan"}
              </span>
            </div>
            {status.tier === "pro" && status.subscription_status && (
              <span className="text-xs text-muted-foreground capitalize">{status.subscription_status}</span>
            )}
          </div>

          {status.monthly_limit !== null ? (
            <div className="mb-4">
              <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
                <span>Questions this month</span>
                <span>{status.usage_this_month} / {status.monthly_limit}</span>
              </div>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${usagePct}%` }}
                />
              </div>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground mb-4">
              {status.usage_this_month} questions this month — unlimited on Pro.
            </p>
          )}

          {error && <p className="text-sm text-destructive mb-3">{error}</p>}

          {status.tier === "pro" ? (
            <Button variant="outline" onClick={handleManage} disabled={loading}>
              {loading ? "Opening…" : "Manage billing"}
            </Button>
          ) : (
            <Button onClick={handleUpgrade} disabled={loading}>
              {loading ? "Redirecting…" : "Upgrade to Pro"}
            </Button>
          )}
        </Card>
      )}
    </div>
  );
}
