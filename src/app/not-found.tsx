import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-3 bg-background p-6 text-center">
      <div className="text-[12px] text-muted-foreground">C-Embedded Agent</div>
      <h1 className="text-[22px] font-semibold">页面不存在</h1>
      <p className="max-w-md text-[13px] text-muted-foreground">
        当前地址不是嵌入式工作台的页面。旧版 Gateway 路由（例如 /providers）已移除。
      </p>
      <div className="mt-2 flex gap-2 text-[13px]">
        <Link href="/" className="rounded-sm bg-primary px-3 py-1.5 text-primary-foreground">
          回到总览
        </Link>
        <Link href="/agent" className="rounded-sm border border-border px-3 py-1.5">
          Agent 工作区
        </Link>
        <Link href="/tools" className="rounded-sm border border-border px-3 py-1.5">
          工具
        </Link>
      </div>
    </div>
  );
}
