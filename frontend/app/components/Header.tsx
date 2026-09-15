"use client";

import { SignInButton, SignUpButton, Show, UserButton } from "@clerk/nextjs";
import { ChartLineUp } from "@phosphor-icons/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import PeloSiMark from "./PeloSiMark";

const NAV_ITEMS = [
  { key: "trade-tracker", href: "/trade-tracker", label: "Trades", icon: ChartLineUp },
] as const;

export default function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background">
      {/* pl-36/pr-6 matches page.tsx's homepage <main> exactly (not just its max-width) — the
          homepage's heroOffsetX measurement computes a transform from the gap between this
          "Home" label and the hero's own content, so if the two containers' padding ever
          diverges, that transform would shift the whole hero to compensate, undoing whatever
          padding change was made there. Keep these in sync. */}
      <div className="mx-auto flex w-full max-w-[96rem] items-center justify-between pl-36 pr-6 py-3">
        <Link
          href="/"
          className="flex items-center gap-2 transition-transform duration-150 ease-out active:scale-[0.97] focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-md border border-border-strong">
            <PeloSiMark size={16} />
          </span>
          <span id="header-home-label" className="text-sm font-semibold tracking-tight text-foreground">
            Home
          </span>
        </Link>

        <nav className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);

              return (
                <Link
                  key={item.key}
                  href={item.href}
                  className={`flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-[color,border-color,transform] duration-150 ease-out active:scale-[0.97] focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70 ${
                    active ? "border-accent text-accent" : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Icon size={16} weight={active ? "fill" : "regular"} aria-hidden="true" />
                  <span className="hidden sm:inline">{item.label}</span>
                </Link>
              );
            })}
          </div>

          <div className="flex items-center gap-2 border-l border-border pl-3">
            <Show when="signed-out">
              <SignInButton>
                <button
                  type="button"
                  className={`cursor-pointer rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70`}
                >
                  Sign in
                </button>
              </SignInButton>
              <SignUpButton>
                <button
                  type="button"
                  className={`cursor-pointer rounded-md bg-accent px-3 py-2 text-sm font-medium text-on-accent transition-[opacity,transform] duration-150 ease-out hover:opacity-90 active:scale-[0.97] focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/70`}
                >
                  Sign up
                </button>
              </SignUpButton>
            </Show>
            <Show when="signed-in">
              <UserButton appearance={{ elements: { avatarBox: "h-7 w-7" } }} />
            </Show>
          </div>
        </nav>
      </div>
    </header>
  );
}
