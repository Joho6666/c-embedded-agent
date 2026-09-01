"use client";

import { useEffect, useState } from "react";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { t } from "@/lib/i18n";
import type { Model, ModelCapability, ModelInput, Provider } from "@/types";

const caps: ModelCapability[] = ["text", "vision", "reasoning", "image", "audio", "embedding", "tools"];

export function ModelDrawer({
  open,
  onOpenChange,
  initial,
  providers,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initial?: Model | null;
  providers: Provider[];
  onSubmit: (input: ModelInput) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [alias, setAlias] = useState("");
  const [providerId, setProviderId] = useState("");
  const [preferred, setPreferred] = useState("");
  const [inputPrice, setInputPrice] = useState("1");
  const [outputPrice, setOutputPrice] = useState("4");
  const [context, setContext] = useState("128000");
  const [selected, setSelected] = useState<ModelCapability[]>(["text"]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(initial?.name ?? "");
    setAlias(initial?.alias ?? "");
    setProviderId(initial?.providerId ?? providers[0]?.id ?? "");
    setPreferred(initial?.preferredProviderId ?? initial?.providerId ?? providers[0]?.id ?? "");
    setInputPrice(String(initial?.inputPrice ?? 1));
    setOutputPrice(String(initial?.outputPrice ?? 4));
    setContext(String(initial?.context ?? 128000));
    setSelected(initial?.capabilities ?? ["text"]);
  }, [open, initial, providers]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent title={initial ? t.models.edit : t.models.add} description={t.models.subtitle}>
        <form
          className="space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setSaving(true);
            try {
              await onSubmit({
                name,
                alias,
                providerId,
                preferredProviderId: preferred || providerId,
                inputPrice: Number(inputPrice) || 0,
                outputPrice: Number(outputPrice) || 0,
                context: Number(context) || 128000,
                capabilities: selected,
              });
              onOpenChange(false);
            } finally {
              setSaving(false);
            }
          }}
        >
          <div className="space-y-1">
            <Label>{t.common.name}</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="space-y-1">
            <Label>{t.models.alias}</Label>
            <Input value={alias} onChange={(e) => setAlias(e.target.value)} required />
          </div>
          <div className="space-y-1">
            <Label>{t.models.provider}</Label>
            <Select value={providerId} onValueChange={setProviderId}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {providers.map((p) => (
                  <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>{t.models.preferred}</Label>
            <Select value={preferred} onValueChange={setPreferred}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {providers.map((p) => (
                  <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="space-y-1">
              <Label>{t.models.input}</Label>
              <Input value={inputPrice} onChange={(e) => setInputPrice(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>{t.models.output}</Label>
              <Input value={outputPrice} onChange={(e) => setOutputPrice(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>{t.models.context}</Label>
              <Input value={context} onChange={(e) => setContext(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1">
            <Label>{t.models.caps}</Label>
            <div className="flex flex-wrap gap-2">
              {caps.map((c) => (
                <label key={c} className="flex items-center gap-1.5 text-[12px]">
                  <Checkbox
                    checked={selected.includes(c)}
                    onCheckedChange={(v) =>
                      setSelected((prev) => (v ? [...prev, c] : prev.filter((x) => x !== c)))
                    }
                  />
                  {t.cap[c]}
                </label>
              ))}
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
