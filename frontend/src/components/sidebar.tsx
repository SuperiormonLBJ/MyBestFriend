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
        className="fixed left-4 top-4 z-50 flex h-10 w-10 items-center justify-center border-2 border-[var(--border)] bg-[var(--background-elevated)] lg:hidden cursor-pointer transition-colors duration-200 hover:bg-[var(--primary)]"
        style={{ boxShadow: "3px 3px 0 var(--border)" }}
      >
        <Menu className="h-5 w-5" strokeWidth={2.5} />
      </button>
      <aside
        className={`fixed left-0 top-0 z-40 flex h-screen w-56 flex-col border-r-2 border-[var(--border)] bg-[var(--background-elevated)] transition-transform duration-200 lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{ boxShadow: "2px 0 0 var(--border)" }}
      >
      <div
        className="flex h-16 items-center gap-2 border-b-2 border-[var(--border)] px-4 bg-[var(--primary)] header-texture"
        style={{ boxShadow: "0 3px 0 var(--border)" }}
      >
        <h1 className="font-heading text-2xl text-[#000000] tracking-wide uppercase">
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
              className={`flex items-center gap-3 px-3 py-3 font-body text-sm font-bold uppercase tracking-wide transition-colors duration-150 cursor-pointer border-l-4 ${
                isActive
                  ? "bg-[var(--primary)] text-[#000000] border-[var(--border)]"
                  : "text-[var(--foreground-muted)] border-transparent hover:border-[var(--border)] hover:bg-[var(--background)] hover:text-[var(--foreground)]"
              }`}
            >
              <Icon className="h-5 w-5 shrink-0" strokeWidth={2.5} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t-2 border-[var(--border)] p-3">
        <button
          type="button"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          className="flex w-full items-center gap-3 border-2 border-transparent px-3 py-2.5 font-body text-sm font-semibold uppercase tracking-wide text-[var(--foreground-muted)] transition-colors duration-150 hover:border-[var(--border)] hover:bg-[var(--background)] hover:text-[var(--foreground)] cursor-pointer"
        >
          {theme === "light" ? (
            <Moon className="h-5 w-5 shrink-0" strokeWidth={2.5} />
          ) : (
            <Sun className="h-5 w-5 shrink-0" strokeWidth={2.5} />
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
        className="fixed inset-0 z-30 bg-black/60 lg:hidden"
      />
    )}
    </>
  );
}
