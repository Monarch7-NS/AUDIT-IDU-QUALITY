import type { Metadata } from "next";
import "./globals.css";
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

export const metadata: Metadata = {
  title: "Audit IDU — Qualité Pédagogique",
  description: "Dashboard d'audit des données pédagogiques IDU — Polytech Annecy-Chambéry",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={cn("h-full", "font-sans", geist.variable)}>
      <body className="min-h-full antialiased">{children}</body>
    </html>
  );
}
