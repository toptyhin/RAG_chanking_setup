export default function ProjectLoading() {
  return (
    <div className="animate-pulse space-y-4" aria-busy="true">
      <div className="h-7 w-52 rounded bg-[var(--border)]" />
      <div className="h-11 rounded bg-[var(--border)]" />
      <div className="h-48 rounded-xl bg-[var(--border)]" />
    </div>
  );
}
