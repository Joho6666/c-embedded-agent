"use client";

import { useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { useGateway } from "@/lib/stores/gateway";
import { copyText } from "@/lib/format";
import { toast } from "sonner";
import { PROVIDER_DESCRIPTORS } from "@/descriptors/providers";

const langs = ["curl", "Python", "JavaScript", "OpenAI SDK", "LangChain"] as const;

export default function DeveloperPage() {
  const url = useGateway((s) => s.settings.gatewayUrl);
  const [lang, setLang] = useState<(typeof langs)[number]>("curl");
  const samples: Record<(typeof langs)[number], string> = {
    curl: `curl ${url}/chat/completions \\
  -H "Authorization: Bearer sk-gw-xxxx" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"coding","messages":[{"role":"user","content":"hello"}]}'`,
    Python: `from openai import OpenAI
client = OpenAI(base_url="${url}", api_key="sk-gw-xxxx")
print(client.chat.completions.create(model="coding", messages=[{"role":"user","content":"hello"}]))`,
    JavaScript: `import OpenAI from "openai";
const client = new OpenAI({ baseURL: "${url}", apiKey: "sk-gw-xxxx" });
await client.chat.completions.create({ model: "coding", messages: [{ role: "user", content: "hello" }] });`,
    "OpenAI SDK": `OPENAI_BASE_URL=${url}
OPENAI_API_KEY=sk-gw-xxxx
# any OpenAI-compatible client`,
    LangChain: `from langchain_openai import ChatOpenAI
llm = ChatOpenAI(base_url="${url}", api_key="sk-gw-xxxx", model="coding")`,
  };

  const endpoints = [
    "GET /v1/models",
    "POST /v1/chat/completions",
    "POST /v1/responses",
    "POST /v1/embeddings",
    "POST /v1/images (if capability)",
    "POST /v1/audio (if capability)",
    "POST /v1/rerank (if capability)",
  ];

  const cols = ["chat", "responses", "streaming", "tools", "vision", "embedding", "image", "audio", "agent"] as const;

  return (
    <div>
      <PageHeader title="开发者接入" description="所有客户端只连一个地址。BASE_URL + Gateway API Key。" />
      <div className="mb-3 rounded-md border border-border bg-card p-3 font-mono text-[12px]">
        BASE_URL={url}
        <br />
        API_KEY=sk-gw-xxxx
      </div>
      <div className="mb-4 grid gap-2 md:grid-cols-2">
        {endpoints.map((e) => (
          <div key={e} className="rounded-sm border border-border px-2 py-1.5 font-mono text-[12px]">
            {e}
          </div>
        ))}
      </div>
      <div className="mb-2 flex flex-wrap gap-1">
        {langs.map((l) => (
          <button
            key={l}
            onClick={() => setLang(l)}
            className={`rounded-sm border px-2 py-1 text-[12px] ${lang === l ? "border-foreground/40 bg-accent" : "border-border"}`}
          >
            {l}
          </button>
        ))}
      </div>
      <pre className="overflow-auto rounded-md border border-border bg-panel-2 p-3 font-mono text-[12px]">{samples[lang]}</pre>
      <Button
        className="mt-2"
        variant="outline"
        onClick={async () => {
          await copyText(samples[lang]);
          toast.success("已复制示例");
        }}
      >
        复制代码
      </Button>
      <div className="mt-6 text-[12px] font-medium">兼容性矩阵</div>
      <div className="mt-2 overflow-auto rounded-md border border-border">
        <table className="gw-table w-full min-w-[720px] text-left text-[11px]">
          <thead className="bg-muted/40 text-muted-foreground">
            <tr>
              <th className="px-2 py-2">Provider</th>
              {cols.map((c) => (
                <th key={c} className="px-2 py-2">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PROVIDER_DESCRIPTORS.filter((d) => d.builtin).map((d) => (
              <tr key={d.id} className="border-t border-border">
                <td className="px-2 py-1.5">{d.name}</td>
                {cols.map((c) => {
                  const ok =
                    d.endpoints.includes(c as never) ||
                    d.capabilities.includes(c as never) ||
                    (c === "streaming" && d.capabilities.includes("streaming"));
                  return (
                    <td key={c} className="px-2 py-1.5">
                      {ok ? "✓" : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
