import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Auto-Trading Bot",
};

export default function AutoTraderLayout({ children }: LayoutProps<"/auto-trader">) {
  return children;
}
