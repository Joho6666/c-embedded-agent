import Link from "next/link";
import { t } from "@/lib/i18n";

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-2">
      <div className="text-[18px] font-semibold">404</div>
      <Link href="/" className="text-[12px] text-muted-foreground underline">
        {t.nav.dashboard}
      </Link>
    </div>
  );
}
