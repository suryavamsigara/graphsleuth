import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Network, ArrowLeft, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { Link } from "react-router-dom";
import CytoscapeComponent from "react-cytoscapejs";

const cyStylesheet: any[] = [
  {
    selector: "node",
    style: {
      "background-color": "#334155",
      "label": "data(label)",
      "color": "#e2e8f0",
      "font-size": "12px",
      "text-valign": "center",
      "text-halign": "center",
      "width": "label",
      "height": "label",
      "padding": "10px",
      "shape": "round-rectangle",
    },
  },
  {
    selector: "node[is_entry = 'true']",
    style: {
      "background-color": "#059669",
      "border-width": 2,
      "border-color": "#34d399",
    },
  },
  {
    selector: "edge",
    style: {
      "width": 2,
      "line-color": "#475569",
      "target-arrow-color": "#475569",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      "label": "data(label)",
      "font-size": "10px",
      "color": "#94a3b8",
    },
  },
];

export default function EvidencePage() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading } = useQuery({
    queryKey: ["evidence-graph", id],
    queryFn: () => api.graph.evidenceGraph(id!),
    enabled: !!id,
  });

  const elements = data
    ? [
        ...data.nodes.map((n: any) => ({
          data: {
            id: n.id,
            label: n.label,
            ...n,
          },
        })),
        ...data.edges.map((e: any) => ({
          data: {
            id: e.id,
            source: e.source,
            target: e.target,
            label: e.label,
          },
        })),
      ]
    : [];

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-slate-800 p-4 flex items-center gap-3">
        <Link
          to="/"
          className="text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2">
            <Network className="w-5 h-5 text-emerald-400" />
            Evidence Path
          </h2>
          <p className="text-xs text-slate-500 font-mono">{id}</p>
        </div>
      </div>

      <div className="flex-1 relative">
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin mr-3" />
            Loading evidence graph...
          </div>
        ) : (
          <CytoscapeComponent
            elements={elements}
            style={{ width: "100%", height: "100%" }}
            stylesheet={cyStylesheet}
            layout={{ name: "cose", padding: 20, animate: true } as any}
            cy={(cy: any) => {
              cy.fit();
              cy.on("tap", "node", (evt: any) => {
                const node = evt.target;
                console.log("Node tapped:", node.data());
              });
            }}
          />
        )}
      </div>
    </div>
  );
}
