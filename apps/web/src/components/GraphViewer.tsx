import { useEffect, useRef, useState, useCallback } from "react";
import cytoscape from "cytoscape";
import { Minus, Plus, Focus, Maximize2 } from "lucide-react";
import { cn } from "../lib/utils";

interface GraphNode {
  id: string;
  label: string;
  type: string;
  description?: string;
  is_entry?: boolean;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

interface GraphViewerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeSelect?: (node: GraphNode | null) => void;
  selectedNodeId?: string | null;
  className?: string;
}

const NODE_COLORS: Record<string, string> = {
  PERSON: "#f59e0b",
  ORGANIZATION: "#3b82f6",
  LOCATION: "#10b981",
  EVENT: "#ef4444",
  PRODUCT: "#8b5cf6",
  CONCEPT: "#06b6d4",
  REGULATION: "#f97316",
  OTHER: "#6b7280",
};

export default function GraphViewer({
  nodes,
  edges,
  onNodeSelect,
  selectedNodeId,
  className,
}: GraphViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [isReady, setIsReady] = useState(false);

  // Initialize Cytoscape once
  useEffect(() => {
    if (!containerRef.current || cyRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      minZoom: 0.15,
      maxZoom: 2.5,
      wheelSensitivity: 0.25,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#1a1a28",
            "background-opacity": 1,
            "border-width": 1.5,
            "border-color": "#2a2a3e",
            "border-opacity": 1,
            "label": "data(label)",
            "color": "#e2e8f0",
            "font-size": "11px",
            "font-weight": 500,
            "text-valign": "bottom",
            "text-halign": "center",
            "text-margin-y": 6,
            "width": 28,
            "height": 28,
            "transition-property": "background-color, border-color",
            "transition-duration": 0.2,
          } as cytoscape.Css.Node,
        },
        {
          selector: "node[?is_entry]",
          style: {
            "border-color": "#34d399",
            "border-width": 2,
            "background-color": "#0c0c12",
            "bounds-expansion": 16,
            },
        },
        {
          selector: "node:selected",
          style: {
            "border-color": "#34d399",
            "border-width": 2.5,
            "background-color": "#0c0c12",
          },
        },
        {
          selector: "node[type]",
          style: {
            "background-color": (ele: any) => {
              const type = ele.data("type") as string;
              return NODE_COLORS[type] || "#6b7280";
            },
            "background-opacity": 0.12,
            "border-color": (ele: any) => {
              const type = ele.data("type") as string;
              return NODE_COLORS[type] || "#6b7280";
            },
          },
        },
        {
          selector: "edge",
          style: {
            "width": 1.5,
            "line-color": "#3f3f4f",
            "line-opacity": 0.5,
            "target-arrow-color": "#3f3f4f",
            "target-arrow-shape": "chevron",
            "curve-style": "bezier",
            "label": "data(label)",
            "font-size": "9px",
            "color": "#5c5c6e",
            "text-background-color": "#0c0c12",
            "text-background-opacity": 0.95,
            "text-background-padding": "2px 5px",
            "text-background-shape": "roundrectangle",
          } as cytoscape.Css.Edge,
        },
        {
          selector: "edge:selected",
          style: {
            "line-color": "#10b981",
            "line-opacity": 0.8,
            "target-arrow-color": "#10b981",
            "width": 2,
          } as cytoscape.Css.Edge,
        },
      ],
      layout: { name: "null" } as any,
    });

    cy.on("tap", "node", (evt) => {
      const data = evt.target.data();
      onNodeSelect?.({
        id: data.id,
        label: data.label,
        type: data.type,
        description: data.description,
        is_entry: data.is_entry,
      });
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        onNodeSelect?.(null);
        cy.elements().unselect();
      }
    });

    cyRef.current = cy;
    setIsReady(true);

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [onNodeSelect]);

  // Update elements when data changes
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !isReady) return;

    cy.elements().remove();

    if (nodes.length === 0) return;

    const cyNodes = nodes.map((n) => ({
      data: {
        id: n.id,
        label: n.label,
        type: n.type,
        description: n.description || "",
        is_entry: n.is_entry || false,
      },
    }));

    const cyEdges = edges.map((e) => ({
      data: {
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
      },
    }));

    cy.add([...cyNodes, ...cyEdges]);

    const layout = cy.layout({
      name: "cose",
      padding: 50,
      nodeRepulsion: 10000,
      idealEdgeLength: 90,
      edgeElasticity: 120,
      nestingFactor: 5,
      gravity: 0.6,
      numIter: 2500,
      initialTemp: 200,
      coolingFactor: 0.95,
      minTemp: 1,
      animate: true,
      animationDuration: 700,
      fit: true,
    });

    layout.run();

    if (selectedNodeId) {
      const node = cy.getElementById(selectedNodeId);
      if (node.length > 0) {
        setTimeout(() => {
          node.select();
          cy.animate({ fit: { eles: node, padding: 100 } }, { duration: 400 });
        }, 750);
      }
    }
  }, [nodes, edges, isReady, selectedNodeId]);

  const zoomIn = useCallback(() => {
    cyRef.current?.zoom(cyRef.current.zoom() * 1.25);
  }, []);

  const zoomOut = useCallback(() => {
    cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  }, []);

  const fit = useCallback(() => {
    cyRef.current?.fit(undefined, 50);
  }, []);

  const hasData = nodes.length > 0;

  return (
    <div className={cn("relative w-full h-full overflow-hidden rounded-xl bg-[#050508]", className)}>
      {!hasData && (
        <div className="absolute inset-0 flex flex-col items-center justify-center z-10">
          <div className="w-10 h-10 rounded-xl bg-[#13131f] border border-[#1a1a28] flex items-center justify-center mb-3">
            <Focus className="w-4 h-4 text-[#3f3f4f]" />
          </div>
          <p className="text-[12px] text-[#5c5c6e]">Search for an entity to visualize</p>
        </div>
      )}

      <div
        ref={containerRef}
        className="w-full h-full"
        style={{ opacity: hasData ? 1 : 0 }}
      />

      {hasData && (
        <div className="absolute bottom-4 right-4 flex flex-col gap-1">
          <button
            onClick={zoomIn}
            className="p-2 rounded-lg bg-[#13131f] border border-[#1a1a28] text-[#5c5c6e] hover:text-[#9494a3] hover:border-[#2a2a3e] transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={zoomOut}
            className="p-2 rounded-lg bg-[#13131f] border border-[#1a1a28] text-[#5c5c6e] hover:text-[#9494a3] hover:border-[#2a2a3e] transition-all"
          >
            <Minus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={fit}
            className="p-2 rounded-lg bg-[#13131f] border border-[#1a1a28] text-[#5c5c6e] hover:text-[#9494a3] hover:border-[#2a2a3e] transition-all"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}