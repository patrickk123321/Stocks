import type { Metadata } from "next";

export async function generateMetadata({ params }: { params: Promise<{ symbol: string }> }): Promise<Metadata> {
  const { symbol } = await params;
  return { title: symbol.toUpperCase() };
}

export default function TickerLayout({ children }: { children: React.ReactNode }) {
  return children;
}
