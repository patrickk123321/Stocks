import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Trade Tracker",
};

export default function TradeTrackerLayout({ children }: LayoutProps<"/trade-tracker">) {
  return children;
}
