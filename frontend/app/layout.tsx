import type { Metadata } from "next";
import { Fira_Code, Fraunces, Public_Sans } from "next/font/google";
import Header from "./components/Header";
import "./globals.css";

const publicSans = Public_Sans({
  variable: "--font-public-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const firaCode = Fira_Code({
  variable: "--font-fira-code",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

// Used narrowly for page-level h1s only (see DESIGN.md) — the one deliberate
// display-type anchor per page, everything else stays Public Sans/Fira Code.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  weight: ["500", "600"],
});

export const metadata: Metadata = {
  title: {
    template: "%s · Pelo$i",
    default: "Pelo$i",
  },
  description: "Pelo$i — track corporate insider, institutional, and congressional trades in one place.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="light"
      className={`${publicSans.variable} ${firaCode.variable} ${fraunces.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <Header />
        {children}
      </body>
    </html>
  );
}
