import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { ConfigProvider } from "@/components/config-provider";
import { Sidebar } from "@/components/sidebar";
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

export const metadata: Metadata = {
  title: "MyBestFriend — Digital Twin",
  description: "Ask anything about the app owner — career, projects, hobbies, and more",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className={cn("font-sans", geist.variable)}>
      <body className="antialiased">
        <ThemeProvider>
          <ConfigProvider>
            <div className="flex h-screen w-full overflow-hidden">
              <Sidebar />
              <main className="flex-1 flex flex-col bg-[var(--background)] pt-16 lg:ml-56 lg:pt-0 overflow-hidden">
                {children}
              </main>
            </div>
          </ConfigProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
