"use client";

import { ChevronDown, ChevronRight, FileCode, Folder } from "lucide-react";
import { useState } from "react";
import type { FileNode } from "@/types/debug";
import { cn } from "@/lib/utils";

function Node({
  node,
  depth,
  active,
  onSelect,
}: {
  node: FileNode;
  depth: number;
  active: string;
  onSelect: (path: string) => void;
}) {
  const [open, setOpen] = useState(true);
  const isFolder = node.type === "folder";
  return (
    <div>
      <button
        className={cn(
          "flex w-full items-center gap-1 rounded-sm px-1 py-0.5 text-left text-[12px] hover:bg-accent",
          !isFolder && active === node.path && "bg-accent text-foreground",
        )}
        style={{ paddingLeft: 6 + depth * 10 }}
        onClick={() => (isFolder ? setOpen(!open) : onSelect(node.path))}
      >
        {isFolder ? (
          open ? (
            <ChevronDown className="size-3 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-3 text-muted-foreground" />
          )
        ) : (
          <FileCode className="size-3 text-info" />
        )}
        {isFolder && <Folder className="size-3 text-warning" />}
        <span className="truncate">{node.name}</span>
      </button>
      {isFolder &&
        open &&
        node.children?.map((c) => (
          <Node key={c.path} node={c} depth={depth + 1} active={active} onSelect={onSelect} />
        ))}
    </div>
  );
}

export function FileTree({
  tree,
  active,
  onSelect,
}: {
  tree: FileNode[];
  active: string;
  onSelect: (path: string) => void;
}) {
  return (
    <div className="h-full overflow-auto py-1">
      {tree.map((n) => (
        <Node key={n.path} node={n} depth={0} active={active} onSelect={onSelect} />
      ))}
    </div>
  );
}
