import Link from "next/link";
import {
  useId,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type KeyboardEvent,
  type ReactNode,
} from "react";

export function Section({
  title,
  children,
  description,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section className="mb-8 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
      <h2 className="text-lg font-semibold">{title}</h2>
      {description ? (
        <p className="mt-1 text-sm text-[var(--muted)]">{description}</p>
      ) : null}
      <div className="mt-4">{children}</div>
    </section>
  );
}

export type TabItem<T extends string = string> = {
  id: T;
  label: string;
  description?: string;
};

export function TabBar<T extends string>({
  tabs,
  value,
  onChange,
  orientation = "horizontal",
  className = "mb-6",
}: {
  tabs: TabItem<T>[];
  value: T;
  onChange: (id: T) => void;
  orientation?: "horizontal" | "vertical";
  className?: string;
}) {
  const vertical = orientation === "vertical";
  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const previousKeys = vertical ? ["ArrowUp"] : ["ArrowLeft"];
    const nextKeys = vertical ? ["ArrowDown"] : ["ArrowRight"];
    let nextIndex = index;
    if (previousKeys.includes(event.key)) nextIndex = (index - 1 + tabs.length) % tabs.length;
    else if (nextKeys.includes(event.key)) nextIndex = (index + 1) % tabs.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = tabs.length - 1;
    else return;
    event.preventDefault();
    onChange(tabs[nextIndex].id);
    document.getElementById(`tab-${tabs[nextIndex].id}`)?.focus();
  }
  const activeDescription = tabs.find((tab) => tab.id === value)?.description;
  return (
    <>
    <div
      role="tablist"
      aria-orientation={orientation}
      className={
        vertical
          ? `flex flex-col gap-0.5 border-r border-[var(--border)] pr-3 ${className}`
          : `flex flex-wrap gap-1 border-b border-[var(--border)] ${className}`
      }
    >
      {tabs.map((tab, index) => {
        const active = tab.id === value;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active}
            aria-controls={`panel-${tab.id}`}
            aria-label={tab.description ? `${tab.label}. ${tab.description}` : tab.label}
            tabIndex={active ? 0 : -1}
            id={`tab-${tab.id}`}
            onClick={() => onChange(tab.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            className={
              vertical
                ? `rounded-md px-3 py-2 text-left text-sm font-medium transition ${
                    active
                      ? "bg-[var(--accent-soft)] text-[var(--fg)]"
                      : "text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--fg)]"
                  }`
                : `relative -mb-px px-4 py-2.5 text-sm font-medium transition ${
                    active
                      ? "border-b-2 border-[var(--accent)] text-[var(--fg)]"
                      : "border-b-2 border-transparent text-[var(--muted)] hover:text-[var(--fg)]"
                  }`
            }
          >
            <span className="block">{tab.label}</span>
            {vertical && tab.description ? (
              <span className="mt-0.5 block text-xs font-normal text-[var(--muted)]">
                {tab.description}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
    {!vertical && activeDescription ? (
      <p className="mt-2 mb-6 text-xs text-[var(--muted)]">{activeDescription}</p>
    ) : null}
    </>
  );
}

export function Button({
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-medium text-[var(--accent-fg)] disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    />
  );
}

export function Input({
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`w-full rounded-md border border-[var(--border)] bg-[var(--surface-input)] px-3 py-2 text-sm text-[var(--fg)] ${className}`}
      {...props}
    />
  );
}

export function Select({
  className = "",
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`w-full rounded-md border border-[var(--border)] bg-[var(--surface-input)] px-3 py-2 text-sm text-[var(--fg)] ${className}`}
      {...props}
    >
      {children}
    </select>
  );
}

export function TextArea({
  className = "",
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={`w-full rounded-md border border-[var(--border)] bg-[var(--surface-input)] px-3 py-2 font-mono text-sm text-[var(--fg)] ${className}`}
      {...props}
    />
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <p className="mt-2 rounded-md border border-[var(--danger-border)] bg-[var(--danger-bg)] px-3 py-2 text-sm text-[var(--danger)]">
      {message}
    </p>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return <label className="mb-1 block text-sm font-medium">{children}</label>;
}

export function StatusDot({
  ok,
  label,
}: {
  ok: boolean;
  label: string;
}) {
  return (
    <span className="inline-flex items-center gap-2 text-sm">
      <span
        className={`inline-block h-2.5 w-2.5 rounded-full ${
          ok ? "bg-[var(--accent)]" : "bg-[var(--border)]"
        }`}
        aria-hidden
      />
      <span className={ok ? "text-[var(--fg)]" : "text-[var(--muted)]"}>
        {label}
      </span>
    </span>
  );
}

export function Callout({
  children,
  tone = "info",
  className = "",
}: {
  children: ReactNode;
  tone?: "info" | "warning";
  className?: string;
}) {
  return (
    <div
      role="note"
      className={`rounded-md border px-3 py-2 text-sm leading-relaxed ${
        tone === "warning"
          ? "border-[var(--warn-border)] bg-[var(--warn-bg)] text-[var(--warn)]"
          : "border-[var(--border)] bg-[var(--accent-soft)] text-[var(--fg)]"
      } ${className}`}
    >
      {children}
    </div>
  );
}

export function WhyItMatters({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <Callout>
      <span className="font-medium">{label}: </span>
      {children}
    </Callout>
  );
}

export function Affects({ label, children }: { label: string; children: ReactNode }) {
  return (
    <p className="mt-1 text-xs text-[var(--muted)]">
      <span className="font-medium text-[var(--fg)]">{label}:</span>{" "}
      {children}
    </p>
  );
}

export function GlossaryTerm({
  children,
  definition,
}: {
  children: ReactNode;
  definition: string;
}) {
  return (
    <span className="group relative inline-flex cursor-help border-b border-dotted border-current">
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-0 z-20 mb-2 hidden w-64 rounded-md border border-[var(--border)] bg-[var(--surface)] p-2 text-xs font-normal text-[var(--fg)] shadow-lg group-hover:block group-focus-within:block"
      >
        {definition}
      </span>
    </span>
  );
}

export function AdvancedSettings({
  label,
  description,
  children,
  open = false,
}: {
  label: string;
  description?: string;
  children: ReactNode;
  open?: boolean;
}) {
  const id = useId();
  return (
    <details open={open} className="rounded-lg border border-[var(--border)] bg-[var(--bg)]/35">
      <summary className="cursor-pointer list-none px-4 py-3 marker:hidden">
        <span className="flex items-center justify-between gap-3">
          <span>
            <span className="block text-sm font-medium">{label}</span>
            {description ? (
              <span id={id} className="mt-0.5 block text-xs font-normal text-[var(--muted)]">
                {description}
              </span>
            ) : null}
          </span>
          <span aria-hidden className="text-[var(--muted)]">＋</span>
        </span>
      </summary>
      <div aria-describedby={description ? id : undefined} className="border-t border-[var(--border)] p-4">
        {children}
      </div>
    </details>
  );
}

export function ButtonLink({
  href,
  children,
  disabled,
  className = "",
}: {
  href: string;
  children: ReactNode;
  disabled?: boolean;
  className?: string;
}) {
  if (disabled) {
    return (
      <span
        className={`inline-flex cursor-not-allowed items-center justify-center rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-medium text-[var(--accent-fg)] opacity-50 ${className}`}
        aria-disabled
      >
        {children}
      </span>
    );
  }
  return (
    <Link
      href={href}
      className={`inline-flex items-center justify-center rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-medium text-[var(--accent-fg)] no-underline hover:opacity-90 ${className}`}
    >
      {children}
    </Link>
  );
}
