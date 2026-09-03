export function ProjectHealth({
  build,
  warnings,
  hardware,
  knowledge,
  agent,
}: {
  build: string;
  warnings: number;
  hardware: string;
  knowledge: string;
  agent: string;
}) {
  const score = Math.max(0, Math.min(100, (build === "PASS" ? 40 : 10) + (warnings === 0 ? 20 : Math.max(0, 20 - warnings * 4)) + (hardware === "Connected" ? 15 : 5) + (knowledge === "Indexed" ? 15 : 5) + (agent === "Ready" ? 10 : 0)));
  return (
    <div className="rounded-md border border-border bg-panel p-3.5">
      <div className="text-[11px] text-muted-foreground">Project Health</div>
      <div className="mt-1 font-mono text-[22px]">{score}</div>
      <dl className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
        <div>Build {build}</div>
        <div>Static Analysis {warnings} warnings</div>
        <div>Hardware {hardware}</div>
        <div>Knowledge {knowledge}</div>
        <div>Agent {agent}</div>
      </dl>
    </div>
  );
}
