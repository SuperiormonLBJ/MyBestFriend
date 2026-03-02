"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageCircle, Settings, SlidersHorizontal, Moon, Sun, Menu } from "lucide-react";
import { useTheme } from "./theme-provider";
import { useConfig } from "./config-provider";
import { useState } from "react";

const navItems = [
  { href: "/chat", label: "Chatbot", icon: MessageCircle },
  { href: "/admin", label: "Admin Panel", icon: Settings },
  { href: "/settings", label: "Settings", icon: SlidersHorizontal },
];

export function Sidebar() {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();
  const { config } = useConfig();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label="Toggle sidebar"
        className="fixed left-4 top-4 z-50 flex h-10 w-10 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--background-elevated)] shadow-[0_0_12px_var(--primary-glow)] lg:hidden cursor-pointer transition-shadow duration-200 hover:shadow-[0_0_18px_var(--primary-glow)]"
      >
        <Menu className="h-5 w-5" strokeWidth={2} />
      </button>
      <aside
        className={`fixed left-0 top-0 z-40 flex h-screen w-56 flex-col border-r border-[var(--border)] bg-[var(--background-elevated)] transition-transform duration-200 lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
      <div className="flex h-16 items-center gap-2 border-b border-[var(--border)] px-4">
        <h1 className="font-heading text-xl font-bold tracking-wider text-[var(--primary)] text-glow">
          {config.app_name}
        </h1>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {navItems.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              onClick={() => setMobileOpen(false)}
              className={`flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-all duration-200 cursor-pointer ${
                isActive
                  ? "bg-[var(--primary)]/20 text-[var(--primary)] border-l-2 border-[var(--primary)] shadow-[0_0_8px_var(--primary-glow)]"
                  : "text-[var(--foreground-muted)] hover:bg-[var(--primary)]/10 hover:text-[var(--foreground)] border-l-2 border-transparent"
              }`}
            >
              <Icon className="h-5 w-5 shrink-0" strokeWidth={2} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-[var(--border)] p-3">
        <button
          type="button"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-[var(--foreground-muted)] transition-all duration-200 hover:bg-[var(--primary)]/10 hover:text-[var(--foreground)] cursor-pointer"
        >
          {theme === "light" ? (
            <Moon className="h-5 w-5 shrink-0" strokeWidth={2} />
          ) : (
            <Sun className="h-5 w-5 shrink-0" strokeWidth={2} />
          )}
          {theme === "light" ? "Dark mode" : "Light mode"}
        </button>
      </div>
    </aside>
    {mobileOpen && (
      <div
        role="button"
        tabIndex={0}
        aria-label="Close sidebar"
        onClick={() => setMobileOpen(false)}
        onKeyDown={(e) => e.key === "Escape" && setMobileOpen(false)}
        className="fixed inset-0 z-30 bg-black/50 lg:hidden"
      />
    )}
    </>
  );
}
