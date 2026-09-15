import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === "development";

// Same source of truth as frontend/app/lib/api.ts's API_BASE.
const backendOrigin = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

// Clerk's publishable key is `pk_<env>_<base64>`, where the base64 payload decodes to the
// Frontend API (FAPI) host Clerk's SDK actually loads its script from and talks to — with a
// trailing "$" to strip. Deriving it here (rather than hardcoding today's dev-instance domain)
// means this doesn't need touching again once a production Clerk key replaces the dev one.
function clerkFrontendApiHost(publishableKey: string | undefined): string | null {
  if (!publishableKey) return null;
  const encoded = publishableKey.split("_").slice(2).join("_");
  try {
    return Buffer.from(encoded, "base64").toString("utf-8").replace(/\$$/, "");
  } catch {
    return null;
  }
}

const clerkFapi = clerkFrontendApiHost(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
// Per Clerk's own CSP docs (clerk.com/docs/security/clerk-csp): the FAPI host itself, plus
// Cloudflare's bot/CAPTCHA challenge and Clerk's fraud-protection hosts. Omitted entirely (empty
// string) if no publishable key is configured, rather than silently allowing nothing and
// breaking Clerk, or guessing a domain.
const clerkScriptSrc = clerkFapi
  ? ` https://${clerkFapi} https://challenges.cloudflare.com https://*.protect.clerk.com`
  : "";
const clerkConnectSrc = clerkFapi ? ` https://${clerkFapi} https://*.protect.clerk.com:*` : "";

// This app has zero third-party scripts/analytics/embeds beyond Clerk (verified across the
// repo). 'unsafe-inline' on script-src/style-src is Next's own documented
// "without nonces" CSP baseline for the App Router — a nonce-based setup would
// force every page into dynamic rendering, disproportionate for this app's
// size. 'unsafe-eval' is dev-only (React's dev-mode error reconstruction).
const csp = [
  "default-src 'self'",
  `connect-src 'self' ${backendOrigin}${clerkConnectSrc}`,
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}${clerkScriptSrc}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: https://img.clerk.com",
  "font-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "frame-src 'self' https://challenges.cloudflare.com https://*.protect.clerk.com",
  "worker-src 'self' blob:",
  "upgrade-insecure-requests",
].join("; ");

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "geolocation=(), camera=(), microphone=(), payment=()" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
  { key: "Content-Security-Policy", value: csp },
];

const nextConfig: NextConfig = {
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
