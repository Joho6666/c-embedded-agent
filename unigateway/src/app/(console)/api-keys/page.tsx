import { Suspense } from "react";
import { KeysPage } from "@/features/keys/KeysPage";
import { PageSkeleton } from "@/components/common/Skeleton";

export default function Page() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <KeysPage />
    </Suspense>
  );
}
