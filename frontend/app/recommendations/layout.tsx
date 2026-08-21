import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Portfolio Recommendations",
};

export default function RecommendationsLayout({ children }: LayoutProps<"/recommendations">) {
  return children;
}
