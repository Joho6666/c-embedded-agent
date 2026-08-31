export function formatNumber(n: number) {
  return new Intl.NumberFormat("en-US").format(Math.round(n));
}

export function formatCompact(n: number) {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n >= 10_000_000 ? 0 : 1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}K`;
  return String(Math.round(n));
}

export function formatUsd(n: number, digits = 2) {
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
}

export function formatMs(n: number) {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}s`;
  return `${Math.round(n)}ms`;
}

export function formatPercent(n: number, digits = 2) {
  return `${n.toFixed(digits)}%`;
}

export function formatTokens(n: number) {
  return formatCompact(n);
}

export function relativeTime(iso?: string) {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.round(diff / 60000);
  if (min < 1) return "刚刚";
  if (min < 60) return `${min} 分钟前`;
  const h = Math.round(min / 60);
  if (h < 24) return `${h} 小时前`;
  const d = Math.round(h / 24);
  return `${d} 天前`;
}

export function formatClock(iso: string) {
  return new Date(iso).toLocaleTimeString("zh-CN", { hour12: false });
}

export function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("zh-CN", { hour12: false });
}

export function maskKey(secret: string) {
  if (secret.length <= 10) return "••••••••";
  return `${secret.slice(0, 7)}…${secret.slice(-4)}`;
}

export function copyText(text: string) {
  return navigator.clipboard.writeText(text);
}

export function remainingLabel(iso?: string) {
  if (!iso) return "";
  const sec = Math.max(0, Math.round((new Date(iso).getTime() - Date.now()) / 1000));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function quotaPct(used: number, limit: number) {
  if (!limit) return 0;
  return Math.min(100, (used / limit) * 100);
}
