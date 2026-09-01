import { Suspense } from "react";
import { ProvidersPage } from "@/features/providers/ProvidersPage";
import { PageSkeleton } from "@/components/common/Skeleton";

export default function Page() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <ProvidersPage />
    </Suspense>
  );
}
