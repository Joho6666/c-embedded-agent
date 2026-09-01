"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { t } from "@/lib/i18n";
import type { ApiKeyInput, CreatedApiKey } from "@/types";

export function ApiKeyDialog({
  open,
  onOpenChange,
  created,
  onCreate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  created: CreatedApiKey | null;
  onCreate: (input: ApiKeyInput) => Promise<void>;
}) {
  const [name, setName] = useState("app-prod");
  const [owner, setOwner] = useState("林舟");
  const [models, setModels] = useState("gpt-4o,claude-sonnet");
  const [budget, setBudget] = useState("500");
  const [rpm, setRpm] = useState("120");
  const [tpm, setTpm] = useState("40000");

  if (created) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent title={t.keys.onceTitle} description={t.keys.onceHint}>
          <div className="rounded-sm border border-border bg-muted/50 p-3 font-mono text-[12px] break-all">{created.fullKey}</div>
          <div className="mt-3 flex justify-end gap-2">
            <Button
              onClick={async () => {
                await navigator.clipboard.writeText(created.fullKey);
                toast.success(t.common.copied);
              }}
            >
              {t.common.copy}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title={t.keys.create} description={t.keys.subtitle}>
        <form
          className="space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            await onCreate({
              name,
              owner,
              allowedModels: models.split(",").map((s) => s.trim()).filter(Boolean),
              budget: Number(budget) || 100,
              rpm: Number(rpm) || 60,
              tpm: Number(tpm) || 20000,
              expiresAt: null,
            });
          }}
        >
          <div className="space-y-1">
            <Label>{t.common.name}</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="space-y-1">
            <Label>{t.keys.owner}</Label>
            <Input value={owner} onChange={(e) => setOwner(e.target.value)} required />
          </div>
          <div className="space-y-1">
            <Label>{t.keys.models}</Label>
            <Input value={models} onChange={(e) => setModels(e.target.value)} />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="space-y-1">
              <Label>{t.keys.budget}</Label>
              <Input value={budget} onChange={(e) => setBudget(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>{t.keys.rpm}</Label>
              <Input value={rpm} onChange={(e) => setRpm(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>{t.keys.tpm}</Label>
              <Input value={tpm} onChange={(e) => setTpm(e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t.common.cancel}
            </Button>
            <Button type="submit">{t.keys.create}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
