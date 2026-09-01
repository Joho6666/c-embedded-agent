export type UserRole = "free" | "standard" | "vip" | "admin";

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  groupId: string;
  planId: string;
  balance: number;
  spend: number;
  keyCount: number;
  requestCount: number;
  status: "active" | "suspended";
}

export interface Group {
  id: string;
  name: string;
  memberCount: number;
  planId: string;
  spend: number;
}

export interface Plan {
  id: string;
  name: string;
  monthlyQuota: number;
  rpm: number;
  tpm: number;
  price: number;
  description: string;
}

export interface UserInput {
  name: string;
  email: string;
  role: UserRole;
  groupId: string;
  planId: string;
  balance: number;
}
