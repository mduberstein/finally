import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "FinAlly",
  description: "AI-powered trading workstation",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
