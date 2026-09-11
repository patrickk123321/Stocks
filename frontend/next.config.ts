import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === "development";

// Same source of truth as frontend/app/lib/api.ts's API_BASE.
const backendOrigin = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

// This app has zero third-party scripts/analytics/embeds (verified across the
// repo). 'unsafe-inline' on script-src/style-src is Next's own documented
// "without nonces" CSP baseline for the App Router — a nonce-based setup would
// force every page into dynamic rendering, disproportionate for this app's
// size. 'unsafe-eval' is dev-only (React's dev-mode error reconstruction).
const csp = [
  "default-src 'self'",
  `connect-src 'self' ${backendOrigin}`,
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
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
