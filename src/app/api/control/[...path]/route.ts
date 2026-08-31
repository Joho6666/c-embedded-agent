import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { createHmac } from "crypto";

export const dynamic = "force-dynamic";

function backend() {
  return process.env.GATEWAY_BACKEND_URL || "http://127.0.0.1:8000";
}

function adminKey() {
  return process.env.GATEWAY_ADMIN_API_KEY || process.env.ADMIN_API_KEY || "";
}

function secret() {
  return process.env.GATEWAY_SECRET_KEY || "";
}

function validSession(token: string | undefined) {
  if (!process.env.ADMIN_USERNAME) return true;
  if (!token || !secret()) return false;
  const [user, exp, sig] = token.split(".");
  if (!user || !exp || !sig) return false;
  if (Date.now() / 1000 > Number(exp)) return false;
  const expect = createHmac("sha256", secret()).update(`${user}.${exp}`).digest("hex");
  return expect === sig && user === process.env.ADMIN_USERNAME;
}

async function proxy(req: NextRequest, path: string[]) {
  const jar = await cookies();
  if (!validSession(jar.get("gw_cp")?.value)) {
    return NextResponse.json({ detail: "unauthorized" }, { status: 401 });
  }
  const key = adminKey();
  if (!key) {
    return NextResponse.json({ detail: "GATEWAY_ADMIN_API_KEY is not set" }, { status: 500 });
  }
  const url = new URL(req.url);
  const target = `${backend()}/admin/${path.join("/")}${url.search}`;
  const headers = new Headers();
  headers.set("Authorization", `Bearer ${key}`);
  const ct = req.headers.get("content-type");
  if (ct) headers.set("Content-Type", ct);
  const init: RequestInit = { method: req.method, headers };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }
  const res = await fetch(target, init);
  const body = await res.text();
  return new NextResponse(body, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") || "application/json" },
  });
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
export async function PATCH(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
export async function DELETE(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
