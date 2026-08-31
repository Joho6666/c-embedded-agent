import { createHmac, createHash } from "crypto";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const username = process.env.ADMIN_USERNAME || "";
  const hash = process.env.ADMIN_PASSWORD_HASH || "";
  const secret = process.env.GATEWAY_SECRET_KEY || "";
  if (!username || !hash || !secret) {
    return NextResponse.json({ detail: "control plane login is not configured" }, { status: 503 });
  }
  const body = (await req.json()) as { username?: string; password?: string };
  const digest = createHash("sha256").update(body.password || "").digest("hex");
  if (body.username !== username || digest !== hash) {
    return NextResponse.json({ detail: "invalid credentials" }, { status: 401 });
  }
  const exp = Math.floor(Date.now() / 1000) + 60 * 60 * 12;
  const sig = createHmac("sha256", secret).update(`${username}.${exp}`).digest("hex");
  const token = `${username}.${exp}.${sig}`;
  const res = NextResponse.json({ ok: true });
  res.cookies.set("gw_cp", token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 12,
  });
  return res;
}
