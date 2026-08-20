/** Relative in-app path safe for redirect (blocks open redirects). */
export function isSafeInternalPath(
  path: string | null | undefined,
): path is string {
  return (
    typeof path === "string" &&
    path.startsWith("/") &&
    !path.startsWith("//") &&
    !path.includes("://")
  );
}

/** Append `from` so the destination can link back to the caller. */
export function withReturnTo(
  target: string,
  returnTo: string | null | undefined,
): string {
  if (!isSafeInternalPath(returnTo)) return target;
  const url = new URL(target, "http://local.invalid");
  url.searchParams.set("from", returnTo);
  return `${url.pathname}${url.search}${url.hash}`;
}

export function readReturnTo(
  search: string | URLSearchParams | null | undefined,
  fallback: string,
): string {
  const params =
    typeof search === "string"
      ? new URLSearchParams(search.startsWith("?") ? search.slice(1) : search)
      : search ?? new URLSearchParams();
  const from = params.get("from");
  return isSafeInternalPath(from) ? from : fallback;
}
