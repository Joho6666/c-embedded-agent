"use client";

import { ChevronDown, ChevronRight, FileCode, Folder } from "lucide-react";
import { useMemo, useState } from "react";
import type { FileNode } from "@/types/debug";
import { useEditor } from "@/lib/stores/editor-store";
import { fileTree as fallback } from "@/lib/mock/files";
import { cn } from "@/lib/utils";

function fromFiles(paths: string[]): FileNode[] {
  const root: FileNode = { name: "project", path: "/", type: "folder", children: [] };
  for (const path of paths.sort()) {
    const parts = path.split("/").filter(Boolean);
    let cur = root;
    let acc = "";
    parts.forEach((part, i) => {
      acc += `/${part}`;
      const isFile = i === parts.length - 1;
      cur.children ??= [];
      let next = cur.children.find((c) => c.path === acc);
      if (!next) {
        next = { name: part, path: acc, type: isFile ? "file" : "folder", children: isFile ? undefined : [] };
        cur.children.push(next);
      }
      cur = next;
    });
  }
  return [root];
}

function Node({
  node,
  depth,
  active,
  dirty,
  onSelect,
}: {
  node: FileNode;
  depth: number;
  active: string;
  dirty: Set<string>;
  onSelect: (path: string) => void;
}) {
  const [open, setOpen] = useState(true);
  const isFolder = node.type === "folder";
  return (
    <div>
      <button
        className={cn(
          "flex w-full items-center gap-1 rounded-sm px-1 py-0.5 text-left text-[12px] hover:bg-accent",
          !isFolder && active === node.path && "bg-accent",
        )}
        style={{ paddingLeft: 6 + depth * 10 }}
        onClick={() => (isFolder ? setOpen(!open) : onSelect(node.path))}
      >
        {isFolder ? (
          open ? <ChevronDown className="size-3 text-muted-foreground" /> : <ChevronRight className="size-3 text-muted-foreground" />
        ) : (
          <FileCode className="size-3 text-info" />
        )}
        {isFolder && <Folder className="size-3 text-warning" />}
        <span className="truncate">{node.name}</span>
        {!isFolder && dirty.has(node.path) && <span className="text-info">●</span>}
      </button>
      {isFolder && open && node.children?.map((c) => (
        <Node key={c.path} node={c} depth={depth + 1} active={active} dirty={dirty} onSelect={onSelect} />
      ))}
    </div>
  );
}

export function FileTree({ active, onSelect }: { active: string; onSelect: (path: string) => void }) {
  const files = useEditor((s) => s.files);
  const tree = useMemo(() => {
    const paths = Object.keys(files);
    return paths.length ? fromFiles(paths) : fallback;
  }, [files]);
  const dirty = useMemo(() => {
    const s = new Set<string>();
    for (const [p, f] of Object.entries(files)) if (f.content !== f.saved) s.add(p);
    return s;
  }, [files]);

  return (
    <div className="h-full overflow-auto py-1">
      {tree.map((n) => (
        <Node key={n.path} node={n} depth={0} active={active} dirty={dirty} onSelect={onSelect} />
      ))}
    </div>
  );
}
