import type { Metadata } from "next";
import { IBM_Plex_Sans } from "next/font/google";
import { AppHeader } from "@/components/app-header";
import { LOCALE_BOOT_SCRIPT } from "@/lib/locale-boot";
import { THEME_BOOT_SCRIPT } from "@/lib/theme-boot";
import { Providers } from "./providers";
import "./globals.css";

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600"],
  variable: "--font-ibm-plex-sans",
});

export const metadata: Metadata = {
  title: "rageval",
  description: "Local RAG Preparer & Evaluator",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={ibmPlexSans.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
        <script dangerouslySetInnerHTML={{ __html: LOCALE_BOOT_SCRIPT }} />
      </head>
      <body className={ibmPlexSans.className}>
        <Providers>
          <div className="mx-auto min-h-screen max-w-[1240px] px-4 py-6">
            <AppHeader />
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}
