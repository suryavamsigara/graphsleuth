interface MetricsPillProps {
  nodes: number;
  edges: number;
  chunks: number;
  documents: number;
  loading?: boolean;
}

const FIELDS: Array<{ key: keyof Omit<MetricsPillProps, "loading">; label: string }> = [
  { key: "nodes", label: "Nodes" },
  { key: "edges", label: "Edges" },
  { key: "chunks", label: "Chunks" },
  { key: "documents", label: "Docs" },
];

export default function MetricsPill(props: MetricsPillProps) {
  return (
    <div className="flex items-stretch rounded-md border border-[var(--hairline)] bg-[var(--panel)] overflow-hidden">
      {FIELDS.map((f, i) => (
        <div
          key={f.key}
          className="flex flex-col justify-center px-3 py-1.5"
          style={{ borderLeft: i === 0 ? "none" : "1px solid var(--hairline)" }}
        >
          <span className="eyebrow leading-none">{f.label}</span>
          <span className="mono text-[13px] font-medium leading-tight text-[var(--ink)] tabular-nums">
            {props.loading ? "—" : props[f.key].toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}
