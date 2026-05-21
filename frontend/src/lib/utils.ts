// 通用工具：cn 用 clsx + tailwind-merge 合并 className，避免 tailwind 冲突
import clsx, { type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// 格式化 ISO 时间字符串。
// tz 为空时使用系统默认时区；否则使用 Intl 时区（需合法 IANA 标识）。
export function formatDateTime(iso?: string | null, tz?: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "-";
  const timeZone = tz || "Asia/Shanghai";
  // 使用 Intl 指定时区
  try {
    return d.toLocaleString("zh-CN", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    // 无效时区回退到本地
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
}
