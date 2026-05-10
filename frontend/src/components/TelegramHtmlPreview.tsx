const BLOCKQUOTE_STYLE =
  "margin:0.35rem 0;padding:0.35rem 0.65rem;border-left:3px solid hsl(var(--border));background:hsl(var(--muted) / 0.35);border-radius:0.25rem;";

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function sanitizeTelegramHtml(value: string): string {
  let html = escapeHtml(value);

  html = html.replace(
    /&lt;(\/?)(b|strong|i|em|u|s|del|strike|code|pre)&gt;/gi,
    "<$1$2>",
  );
  html = html.replace(
    /&lt;blockquote(?:\s+expandable)?&gt;/gi,
    `<blockquote style="${BLOCKQUOTE_STYLE}">`,
  );
  html = html.replace(/&lt;\/blockquote&gt;/gi, "</blockquote>");

  return html;
}

export function TelegramHtmlPreview({
  value,
  mode,
}: {
  value: string;
  mode?: "html" | "markdown" | "plain";
}) {
  if (mode && mode !== "html") {
    return (
      <pre className="whitespace-pre-wrap break-words font-sans text-muted-foreground">
        {value}
      </pre>
    );
  }

  return (
    <div
      className="whitespace-pre-wrap break-words text-muted-foreground [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_pre]:rounded [&_pre]:bg-muted [&_pre]:p-2"
      dangerouslySetInnerHTML={{ __html: sanitizeTelegramHtml(value) }}
    />
  );
}
