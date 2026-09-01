"use client";

import { useEffect, useState } from "react";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { t } from "@/lib/i18n";
import { defaultBaseUrls } from "@/lib/provider-templates";
import type { Provider, ProviderInput, ProviderTemplate } from "@/types";

const templates: ProviderTemplate[] = ["openai", "anthropic", "gemini", "openrouter", "newapi", "oneapi", "custom"];

export function ProviderDrawer({
  open,
  onOpenChange,
  initial,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initial?: Provider | null;
  onSubmit: (input: ProviderInput) => Promise<void>;
}) {
  const [type, setType] = useState<ProviderTemplate>(initial?.type ?? "openai");
  const [name, setName] = useState(initial?.name ?? "");
  const [baseUrl, setBaseUrl] = useState(initial?.baseUrl ?? defaultBaseUrls.openai);
  const [priority, setPriority] = useState(String(initial?.priority ?? 3));
  const [weight, setWeight] = useState(String(initial?.weight ?? 10));
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setType(initial?.type ?? "openai");
    setName(initial?.name ?? "");
    setBaseUrl(initial?.baseUrl ?? defaultBaseUrls.openai);
    setPriority(String(initial?.priority ?? 3));
    setWeight(String(initial?.weight ?? 10));
  }, [open, initial]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent title={initial ? t.providers.edit : t.providers.add} description={t.providers.subtitle}>
        <form
          className="space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setSaving(true);
            try {
              await onSubmit({
                name: name || t.templates[type],
                type,
                baseUrl,
                priority: Number(priority) || 3,
                weight: Number(weight) || 10,
              });
              onOpenChange(false);
            } finally {
              setSaving(false);
            }
          }}
        >
          <div className="space-y-1">
            <Label>{t.providers.template}</Label>
            <Select
              value={type}
              onValueChange={(v) => {
                const next = v as ProviderTemplate;
                setType(next);
                if (!initial) setBaseUrl(defaultBaseUrls[next]);
                if (!name) setName(t.templates[next]);
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {templates.map((tpl) => (
                  <SelectItem key={tpl} value={tpl}>
                    {t.templates[tpl]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>{t.common.name}</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="space-y-1">
            <Label>{t.providers.baseUrl}</Label>
            <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label>{t.providers.priority}</Label>
              <Input type="number" min={1} value={priority} onChange={(e) => setPriority(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>{t.providers.weight}</Label>
              <Input type="number" min={1} value={weight} onChange={(e) => setWeight(e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t.common.cancel}
            </Button>
            <Button type="submit" disabled={saving}>
              {t.common.save}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
