import type { FeatureInfo } from "@/api/types";

export const FEATURE_CONFIG_PAGE_KEYS = new Set([
  "auto_reply",
  "autorepeat",
  "chatgpt_image",
  "codex_image",
  "scheduler",
  "game24",
]);

export function featureConfigPath(
  aid: number | null | undefined,
  key: string,
  feature?: Pick<FeatureInfo, "config_schema"> | null,
): string | null {
  if (!aid || !key) return null;
  if (!FEATURE_CONFIG_PAGE_KEYS.has(key) && !feature?.config_schema) return null;
  return `/accounts/${aid}/features/${key}`;
}
