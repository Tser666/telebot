const BLOCKQUOTE_STYLE =
  "margin:0.35rem 0;padding:0.35rem 0.65rem;border-left:3px solid rgba(255,255,255,.65);background:rgba(255,255,255,.14);border-radius:0.45rem;";

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
  title = "TelePilot",
}: {
  value: string;
  mode?: "html" | "markdown" | "plain";
  title?: string;
}) {
  const content = value || "预览内容为空。";
  const rendered =
    mode && mode !== "html" ? (
      <pre className="whitespace-pre-wrap break-words font-sans text-white">
        {content}
      </pre>
    ) : (
      <div
        className="whitespace-pre-wrap break-words text-white [&_a]:text-white [&_code]:rounded [&_code]:bg-white/15 [&_code]:px-1 [&_code]:py-0.5 [&_pre]:rounded [&_pre]:bg-white/15 [&_pre]:p-2"
        dangerouslySetInnerHTML={{ __html: sanitizeTelegramHtml(content) }}
      />
    );

  return (
    <div className="rounded-2xl border bg-gradient-to-b from-sky-50 to-emerald-50 p-4 text-xs dark:from-sky-950/30 dark:to-emerald-950/20">
      <div className="space-y-2.5">
        <div className="w-fit max-w-[78%] rounded-2xl rounded-bl-lg border bg-card px-3.5 py-2.5 text-foreground shadow-sm sm:max-w-[66%]">
          <div className="font-medium text-[11px] text-muted-foreground">示例用户</div>
          <div className="mt-1">请根据下面内容回复。</div>
        </div>

        <div className="ml-auto w-fit max-w-[88%] rounded-2xl rounded-br-lg bg-sky-500 px-3.5 py-2.5 text-white shadow-sm sm:max-w-[76%]">
          <div className="mb-1.5 text-[11px] font-semibold text-white/85">{title}</div>
          {rendered}
          <div className="mt-1.5 text-right text-[10px] leading-none text-white/75">
            12:30 ✓✓
          </div>
        </div>
      </div>
    </div>
  );
}

export interface TelegramHtmlPreviewMessage {
  title?: string;
  value: string;
  mode?: "html" | "markdown" | "plain";
}

export function TelegramHtmlPreviewThread({
  messages,
}: {
  messages: TelegramHtmlPreviewMessage[];
}) {
  const renderedMessages = messages.length > 0
    ? messages
    : [{ title: "TelePilot", value: "预览内容为空。", mode: "plain" as const }];

  return (
    <div className="rounded-2xl border bg-gradient-to-b from-sky-50 to-emerald-50 p-4 text-xs dark:from-sky-950/30 dark:to-emerald-950/20">
      <div className="space-y-2.5">
        <div className="w-fit max-w-[78%] rounded-2xl rounded-bl-lg border bg-card px-3.5 py-2.5 text-foreground shadow-sm sm:max-w-[66%]">
          <div className="font-medium text-[11px] text-muted-foreground">示例用户</div>
          <div className="mt-1">发送指令并参与竞猜。</div>
        </div>

        {renderedMessages.map((message, index) => (
          <div
            key={`${message.title ?? "preview"}-${index}`}
            className="ml-auto w-fit max-w-[88%] rounded-2xl rounded-br-lg bg-sky-500 px-3.5 py-2.5 text-white shadow-sm sm:max-w-[76%]"
          >
            <div className="mb-1.5 text-[11px] font-semibold text-white/85">
              {message.title || "TelePilot"}
            </div>
            {renderTelegramPreviewContent(message.value, message.mode)}
            <div className="mt-1.5 text-right text-[10px] leading-none text-white/75">
              12:{String(30 + index).padStart(2, "0")} ✓✓
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function renderTelegramPreviewContent(
  value: string,
  mode?: "html" | "markdown" | "plain",
) {
  const content = value || "预览内容为空。";
  if (mode && mode !== "html") {
    return (
      <pre className="whitespace-pre-wrap break-words font-sans text-white">
        {content}
      </pre>
    );
  }

  return (
    <div
      className="whitespace-pre-wrap break-words text-white [&_a]:text-white [&_code]:rounded [&_code]:bg-white/15 [&_code]:px-1 [&_code]:py-0.5 [&_pre]:rounded [&_pre]:bg-white/15 [&_pre]:p-2"
      dangerouslySetInnerHTML={{ __html: sanitizeTelegramHtml(content) }}
    />
  );
}

export function TelegramHtmlContentPreview({
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
