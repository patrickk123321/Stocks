import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Watchlist",
};

export default function WatchlistLayout({ children }: LayoutProps<"/watchlist">) {
  return children;
}
