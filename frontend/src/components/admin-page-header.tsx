"use client";

import Link from "next/link";

const headerCls =
  "shrink-0 border-b-2 border-[var(--border)] bg-[var(--primary)] px-6 py-4 header-texture";
const backLinkCls =
  "mb-2 inline-block font-body text-sm font-semibold text-[#000000]/60 hover:text-[#000000]";
const titleCls = "font-heading text-3xl text-[#000000] uppercase tracking-wide";
const subtitleCls =
  "mt-0.5 font-body text-base font-bold text-[#000000]/75 uppercase tracking-widest";

type AdminPageHeaderProps = {
  title: string;
  subtitle: string;
  actions?: React.ReactNode;
};

export function AdminPageHeader({ title, subtitle, actions }: AdminPageHeaderProps) {
  return (
    <header className={headerCls}>
      <Link href="/admin" className={backLinkCls}>
        ← Admin Panel
      </Link>
      <div className="flex items-center justify-between">
        <div>
          <h2 className={titleCls}>{title}</h2>
          <p className={subtitleCls}>{subtitle}</p>
        </div>
        {actions}
      </div>
    </header>
  );
}
