import Link from "next/link";
import { auth } from "@clerk/nextjs/server";
import { Check, Minus } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

// Marketing copy, deliberately static: this page must render even when the API is
// down. Source of truth for the limits is backend/app/config.py (FREE_TIER_* /
// PRO_TIER_*) and for the price, the Stripe product — keep them in sync by hand.
const PLANS = [
  {
    name: "Free",
    price: "CA$0",
    cadence: "forever",
    blurb: "Enough to explore your data and see whether the agent earns its keep.",
    features: [
      { label: "20 questions per month", included: true },
      { label: "Up to 1,000 rows per result", included: true },
      { label: "5 second query timeout", included: true },
      { label: "Connect your own Postgres database", included: true },
      { label: "Credentials encrypted at rest", included: true },
      { label: "Unlimited questions", included: false },
    ],
    cta: "Start for free",
    featured: false,
  },
  {
    name: "Pro",
    price: "CA$20",
    cadence: "per month",
    blurb: "For anyone actually leaning on this day to day.",
    features: [
      { label: "Unlimited questions", included: true },
      { label: "Up to 5,000 rows per result", included: true },
      { label: "15 second query timeout", included: true },
      { label: "Connect your own Postgres database", included: true },
      { label: "Credentials encrypted at rest", included: true },
      { label: "Cancel anytime, self-serve", included: true },
    ],
    cta: "Upgrade to Pro",
    featured: true,
  },
];

export default async function PricingPage() {
  const { userId } = await auth();

  // The upgrade action itself lives only on /settings/billing, which already knows
  // how to show "Manage billing" to someone who is on Pro. Starting checkout from
  // here as well would let an existing subscriber open a second subscription.
  const ctaHref = userId ? "/settings/billing" : "/sign-up";

  return (
    <div className="flex flex-col min-h-screen">
      <header className="border-b px-6 py-4 flex items-center justify-between">
        <Link href="/" className="font-semibold text-lg tracking-tight">SQL Copilot</Link>
        <div className="flex gap-3 items-center">
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

      <main className="flex-1 px-6 py-20">
        <div className="max-w-3xl mx-auto text-center mb-14">
          <h1 className="text-4xl font-bold tracking-tight mb-4">Simple, predictable pricing.</h1>
          <p className="text-lg text-muted-foreground">
            Start free — no card required. Upgrade when you need more than the free tier allows.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
          {PLANS.map((plan) => (
            <Card
              key={plan.name}
              className={cn("p-6", plan.featured && "ring-2 ring-primary")}
            >
              <CardHeader className="px-0">
                <CardTitle className="text-base">{plan.name}</CardTitle>
                <CardDescription>{plan.blurb}</CardDescription>
              </CardHeader>

              <CardContent className="px-0">
                <div className="flex items-baseline gap-2 mb-6">
                  <span className="text-4xl font-bold tracking-tight">{plan.price}</span>
                  <span className="text-sm text-muted-foreground">{plan.cadence}</span>
                </div>

                <ul className="space-y-2.5 mb-8">
                  {plan.features.map((f) => (
                    <li
                      key={f.label}
                      className={cn(
                        "flex items-start gap-2.5 text-sm",
                        !f.included && "text-muted-foreground/60"
                      )}
                    >
                      {f.included ? (
                        <Check className="w-4 h-4 mt-0.5 shrink-0 text-primary" />
                      ) : (
                        <Minus className="w-4 h-4 mt-0.5 shrink-0" />
                      )}
                      <span>{f.label}</span>
                    </li>
                  ))}
                </ul>

                <Link
                  href={ctaHref}
                  className={cn(
                    buttonVariants({
                      size: "lg",
                      variant: plan.featured ? "default" : "outline",
                    }),
                    "w-full"
                  )}
                >
                  {userId ? "Manage plan" : plan.cta}
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>

        <p className="text-center text-sm text-muted-foreground mt-10">
          Every plan runs queries through the same read-only safety sandbox — the agent can never
          write to your database.
        </p>
      </main>

      <footer className="border-t px-6 py-6 text-center text-sm text-muted-foreground">
        SQL Copilot — built by Alan Chen
      </footer>
    </div>
  );
}
