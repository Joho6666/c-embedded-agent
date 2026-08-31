"use client";

import type { FormField } from "@/types";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export function DynamicForm({
  fields,
  values,
  onChange,
}: {
  fields: FormField[];
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
}) {
  const groups = Array.from(new Set(fields.map((f) => f.group ?? "其他")));
  return (
    <div className="space-y-4">
      {groups.map((g) => (
        <div key={g}>
          <div className="mb-2 text-[10px] tracking-wide text-muted-foreground uppercase">{g}</div>
          <div className="grid gap-2.5">
            {fields
              .filter((f) => (f.group ?? "其他") === g)
              .map((f) => (
                <div key={f.key} className="grid gap-1">
                  <Label>
                    {f.label}
                    {f.required ? " *" : ""}
                  </Label>
                  {f.type === "select" ? (
                    <Select value={values[f.key] ?? ""} onValueChange={(v) => onChange(f.key, v)}>
                      <SelectTrigger>
                        <SelectValue placeholder={f.placeholder ?? "选择"} />
                      </SelectTrigger>
                      <SelectContent>
                        {(f.options ?? []).map((o) => (
                          <SelectItem key={o.value} value={o.value}>
                            {o.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : f.type === "textarea" || f.type === "headers" ? (
                    <Textarea
                      placeholder={f.placeholder}
                      value={values[f.key] ?? ""}
                      onChange={(e) => onChange(f.key, e.target.value)}
                    />
                  ) : (
                    <Input
                      type={f.type === "password" ? "password" : f.type === "number" ? "number" : "text"}
                      placeholder={f.placeholder}
                      value={values[f.key] ?? ""}
                      onChange={(e) => onChange(f.key, e.target.value)}
                    />
                  )}
                  {f.help && <div className="text-[10px] text-muted-foreground">{f.help}</div>}
                </div>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}
