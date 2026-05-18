export const FEATURE_CONFIG_PAGE_KEYS = new Set([
  "auto_reply",
  "autorepeat",
  "chatgpt_image",
  "codex_image",
  "forward",
  "scheduler",
  "game24",
]);

export function featureConfigPath(
  aid: number | null | undefined,
  key: string,
): string | null {
  if (!aid || !key) return null;
  return `/accounts/${aid}/features/${key}`;
}
