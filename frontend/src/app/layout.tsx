import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { Sidebar } from "@/components/sidebar";

export const metadata: Metadata = {
  title: "MyBestFriend — Digital Twin",
  description: "Ask anything about Beiji — career, projects, hobbies, and more",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <ThemeProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="relative z-10 min-h-screen flex-1 flex-col bg-[var(--background)] pt-16 lg:ml-56 lg:pt-0 flex">
              {children}
            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
