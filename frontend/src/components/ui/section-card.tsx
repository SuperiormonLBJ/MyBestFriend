"use client";

type SectionCardProps = {
  icon: React.ReactNode;
  title: string;
  description?: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
};

export function SectionCard({
  icon,
  title,
  description,
  badge,
  children,
}: SectionCardProps) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--background-elevated)]">
      <div className="flex items-start justify-between gap-3 border-b border-[var(--border)] px-6 py-4">
        <div className="flex items-center gap-2.5">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border-2 border-[var(--border)] bg-[var(--surface)] text-[var(--foreground)]">
            {icon}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--foreground)]">{title}</h3>
            {description != null && (
              <p className="mt-0.5 text-xs text-[var(--foreground-muted)]">{description}</p>
            )}
          </div>
        </div>
        {badge}
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}
