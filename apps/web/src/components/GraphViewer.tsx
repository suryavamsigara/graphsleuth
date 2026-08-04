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

export interface EvidencePath {
  nodeIds: string[];
  edgeIds: string[];
}

interface GraphViewerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeSelect?: (node: GraphNode | null) => void;
  selectedNodeId?: string | null;
  evidencePath?: EvidencePath | null; // when set, everything outside it dims ("redacted")
  className?: string;
}

const NODE_COLORS: Record<string, string> = {
  PERSON: "#f2a33e",
  ORGANIZATION: "#6c8ef5",
  LOCATION: "#5fd0a7",
  EVENT: "#ef5b4e",
  PRODUCT: "#b98cf2",
  CONCEPT: "#4fc3d9",
  REGULATION: "#e08a3c",
  OTHER: "#7d818c",
};

export default function GraphViewer({
  nodes,
  edges,
  onNodeSelect,
  selectedNodeId,
  evidencePath,
  className,
}: GraphViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const onNodeSelectRef = useRef(onNodeSelect);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    onNodeSelectRef.current = onNodeSelect;
  }, [onNodeSelect]);


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
            "background-color": "#181a20",
            "background-opacity": 1,
            "border-width": 1.5,
            "border-color": "#262a33",
            "border-opacity": 1,
            label: "data(label)",
            color: "#e9e7e0",
            "font-size": "11px",
            "font-family": "IBM Plex Mono, monospace",
            "font-weight": 500,
            "text-valign": "bottom",
            "text-halign": "center",
            "text-margin-y": 7,
            width: 26,
            height: 26,
            "transition-property": "background-color, border-color, opacity",
            "transition-duration": 0.25,
          } as cytoscape.Css.Node,
        },
        // Entry nodes read as map pins: filled dot + a soft red halo.
        // (Cytoscape core has no `shadow-*` style props — `overlay-*` is
        // the real halo mechanism, so that's what actually renders one.)
        {
          selector: "node[?is_entry]",
          style: {
            "border-color": "#ef5b4e",
            "border-width": 2.5,
            "background-color": "#ef5b4e",
            "background-opacity": 0.9,
            width: 20,
            height: 20,
            "overlay-color": "#ef5b4e",
            "overlay-opacity": 0.25,
            "overlay-padding": 6,
          } as any,
        },
        {
          selector: "node:selected",
          style: {
            "border-color": "#f2a33e",
            "border-width": 2.5,
            "background-color": "#181a20",
          },
        },
        {
          selector: "node[type]",
          style: {
            "background-color": (ele: any) => NODE_COLORS[ele.data("type") as string] || "#7d818c",
            "background-opacity": 0.14,
            "border-color": (ele: any) => NODE_COLORS[ele.data("type") as string] || "#7d818c",
          },
        },
        // Redacted: outside the current evidence path
        {
          selector: "node.redacted",
          style: {
            "background-opacity": 0.04,
            "border-opacity": 0.25,
            color: "#5d616b",
            "text-opacity": 0.5,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#2e323c",
            "line-opacity": 0.6,
            "target-arrow-color": "#2e323c",
            "target-arrow-shape": "chevron",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": "9px",
            "font-family": "IBM Plex Mono, monospace",
            color: "#5d616b",
            "text-background-color": "#101217",
            "text-background-opacity": 0.95,
            "text-background-padding": "2px 5px",
            "text-background-shape": "roundrectangle",
          } as cytoscape.Css.Edge,
        },
        {
          selector: "edge.redacted",
          style: { "line-opacity": 0.08, "text-opacity": 0.15 },
        },
        // The evidence string: the traversed path, lit up like red string on cork
        {
          selector: "edge.evidence",
          style: {
            "line-color": "#f2a33e",
            "line-opacity": 1,
            "target-arrow-color": "#f2a33e",
            width: 2.5,
            "overlay-color": "#f2a33e",
            "overlay-opacity": 0.2,
            "overlay-padding": 4,
            color: "#f2a33e",
            "text-background-color": "#101217",
          } as any,
        },
        {
          selector: "node.evidence",
          style: {
            "border-color": "#f2a33e",
            "border-width": 2,
          },
        },
        {
          selector: "edge:selected",
          style: {
            "line-color": "#5fd0a7",
            "line-opacity": 0.9,
            "target-arrow-color": "#5fd0a7",
            width: 2.5,
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
  }, []);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const handleVisibility = () => {
      if (document.visibilityState === "visible" && nodes.length > 0) {
        // Small delay to let browser finish compositing
        requestAnimationFrame(() => {
          cy.resize();
          cy.fit(undefined, 50);
        });
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [nodes.length]);

  // Rebuild elements when data changes
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !isReady) return;

    cy.elements().remove();
    if (nodes.length === 0) {
      setIsReady(true); // keep ready state, just empty
      return;
    }

    const cyNodes = nodes.map((n) => ({
      data: { id: n.id, label: n.label, type: n.type, description: n.description || "", is_entry: n.is_entry || false },
    }));
    const cyEdges = edges.map((e) => ({ data: { id: e.id, source: e.source, target: e.target, label: e.label } }));

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
    } as any);

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

  // Apply / clear the evidence-path highlight (dim everything else, light the trail)
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !isReady) return;

    cy.elements().removeClass("evidence redacted");

    if (!evidencePath || evidencePath.nodeIds.length === 0) return;

    const nodeSet = new Set(evidencePath.nodeIds);
    const edgeSet = new Set(evidencePath.edgeIds);

    cy.nodes().forEach((n) => {
      if (nodeSet.has(n.id())) n.addClass("evidence");
      else n.addClass("redacted");
    });
    cy.edges().forEach((e) => {
      if (edgeSet.has(e.id())) e.addClass("evidence");
      else e.addClass("redacted");
    });
  }, [evidencePath, isReady]);

  const zoomIn = useCallback(() => cyRef.current?.zoom(cyRef.current.zoom() * 1.25), []);
  const zoomOut = useCallback(() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8), []);
  const fit = useCallback(() => cyRef.current?.fit(undefined, 50), []);

  const hasData = nodes.length > 0;

  return (
    <div
      className={cn("relative w-full h-full overflow-hidden rounded-lg", className)}
      style={{ background: "var(--board)", backgroundImage: "var(--board-dot)", backgroundSize: "18px 18px" }}
    >
      {!hasData && (
        <div className="absolute inset-0 flex flex-col items-center justify-center z-10">
          <div className="w-10 h-10 rounded-lg bg-[var(--panel-raised)] border border-[var(--hairline)] flex items-center justify-center mb-3 rotate-[-2deg]">
            <Focus className="w-4 h-4 text-[var(--ink-faint)]" />
          </div>
          <p className="eyebrow">Board is empty — search an entity to pin it</p>
        </div>
      )}

      <div ref={containerRef} className="w-full h-full" style={{ opacity: hasData ? 1 : 0 }} />

      {hasData && (
        <div className="absolute bottom-4 right-4 flex flex-col gap-1">
          <button onClick={zoomIn} className="p-2 rounded-md bg-[var(--panel-raised)] border border-[var(--hairline)] text-[var(--ink-faint)] hover:text-[var(--ink)] hover:border-[var(--hairline-strong)] transition-all">
            <Plus className="w-3.5 h-3.5" />
          </button>
          <button onClick={zoomOut} className="p-2 rounded-md bg-[var(--panel-raised)] border border-[var(--hairline)] text-[var(--ink-faint)] hover:text-[var(--ink)] hover:border-[var(--hairline-strong)] transition-all">
            <Minus className="w-3.5 h-3.5" />
          </button>
          <button onClick={fit} className="p-2 rounded-md bg-[var(--panel-raised)] border border-[var(--hairline)] text-[var(--ink-faint)] hover:text-[var(--ink)] hover:border-[var(--hairline-strong)] transition-all">
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
