"use client";

import { useEffect, useState } from "react";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { t } from "@/lib/i18n";
import type { Group, Plan, User, UserInput, UserRole } from "@/types";

const roles: UserRole[] = ["free", "standard", "vip", "admin"];

export function UserDrawer({
  open,
  onOpenChange,
  initial,
  groups,
  plans,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initial?: User | null;
  groups: Group[];
  plans: Plan[];
  onSubmit: (input: UserInput) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<UserRole>("standard");
  const [groupId, setGroupId] = useState("");
  const [planId, setPlanId] = useState("");
  const [balance, setBalance] = useState("100");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(initial?.name ?? "");
    setEmail(initial?.email ?? "");
    setRole(initial?.role ?? "standard");
    setGroupId(initial?.groupId ?? groups[0]?.id ?? "");
    setPlanId(initial?.planId ?? plans[0]?.id ?? "");
    setBalance(String(initial?.balance ?? 100));
  }, [open, initial, groups, plans]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent title={initial ? t.users.edit : t.users.add} description={t.users.subtitle}>
        <form
          className="space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setSaving(true);
            try {
              await onSubmit({
                name,
                email,
                role,
                groupId,
                planId,
                balance: Number(balance) || 0,
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
            <Label>{t.users.email}</Label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="space-y-1">
            <Label>{t.common.type}</Label>
            <Select value={role} onValueChange={(v) => setRole(v as UserRole)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {roles.map((r) => (
                  <SelectItem key={r} value={r}>{t.role[r]}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>{t.users.groups}</Label>
            <Select value={groupId} onValueChange={setGroupId}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {groups.map((g) => (
                  <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>{t.users.plans}</Label>
            <Select value={planId} onValueChange={setPlanId}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {plans.map((p) => (
                  <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>{t.users.balance}</Label>
            <Input value={balance} onChange={(e) => setBalance(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>{t.common.cancel}</Button>
            <Button type="submit" disabled={saving}>{t.common.save}</Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
