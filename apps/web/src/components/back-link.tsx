import Link from "next/link";

export function BackLink({
  href,
  label,
}: {
  href: string;
  label: string;
}) {
  return (
    <Link
      href={href}
      className="inline-flex size-8 shrink-0 items-center justify-center rounded-md text-[var(--muted)] no-underline hover:bg-[var(--accent-soft)] hover:text-[var(--fg)] hover:no-underline focus:no-underline active:no-underline"
      aria-label={label}
      title={label}
    >
      <svg
        aria-hidden
        viewBox="0 0 16 16"
        className="size-4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M10 3 5 8l5 5" />
      </svg>
    </Link>
  );
}
