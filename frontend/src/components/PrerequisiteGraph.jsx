import { useState, useMemo, useRef, useId } from 'react';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Network,
  GitBranch,
  AlertTriangle,
  ArrowRight,
  Info,
  Sparkles,
} from 'lucide-react';

const VIEW_W = 920;
const VIEW_H = 500;

const CLUSTER_PALETTE = [
  { fill: '#60A5FA', stroke: '#2563EB', edge: '#3B82F6' }, // Sky Blue
  { fill: '#A78BFA', stroke: '#7C3AED', edge: '#8B5CF6' }, // Violet
  { fill: '#4ADE80', stroke: '#16A34A', edge: '#22C55E' }, // Emerald
  { fill: '#FACC15', stroke: '#CA8A04', edge: '#EAB308' }, // Gold Amber
  { fill: '#F472B6', stroke: '#DB2777', edge: '#EC4899' }, // Magenta
  { fill: '#F87171', stroke: '#DC2626', edge: '#EF4444' }, // Coral Red
  { fill: '#2DD4BF', stroke: '#0D9488', edge: '#14B8A6' }, // Teal
];

const REJECTED_STYLE = {
  fill: '#FDA4AF',
  stroke: '#E11D48',
  edge: '#E11D48',
};

function hashStr(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967295;
}

function formatShortLabel(name) {
  if (!name) return '';
  const trimmed = String(name).trim();
  const colonIdx = trimmed.lastIndexOf(': ');
  const candidate = colonIdx > 0 && trimmed.length > 26 ? trimmed.slice(colonIdx + 2).trim() : trimmed;
  if (candidate.length <= 24) return candidate;
  return `${candidate.slice(0, 22).trim()}…`;
}

export default function PrerequisiteGraph({
  nodes = [],
  edges = [],
  mode = 'curriculum', // 'curriculum' | 'mastery'
  title = 'Prerequisite Knowledge Graph',
  subtitle = 'Directed network of concepts and dependency links. Drag nodes or click to inspect connections.',
  height = 460,
  onNodeAction = null,
  actionLabel = 'Target This Topic',
  actionDisabled = false,
}) {
  const uid = useId().replace(/:/g, '');
  const svgRef = useRef(null);

  const [layoutMode, setLayoutMode] = useState('network'); // 'network' | 'dag'
  const [showRejectedCycles, setShowRejectedCycles] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [hoveredId, setHoveredId] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [customPos, setCustomPos] = useState({});

  const [dragState, setDragState] = useState(null); // { type: 'node'|'pan', id?, startX, startY, origX, origY, moved }

  // Normalize nodes & edges cleanly
  const graphData = useMemo(() => {
    const nodeMap = new Map();
    nodes.forEach((n, idx) => {
      const id = String(n.id ?? n.label ?? idx);
      nodeMap.set(id, {
        ...n,
        id,
        label: String(n.label ?? n.name ?? id),
        shortLabel: formatShortLabel(n.label ?? n.name ?? id),
      });
    });

    const validEdges = [];
    const rejectedEdges = [];

    edges.forEach((e, idx) => {
      const from = String(e.from ?? '');
      const to = String(e.to ?? '');
      if (!from || !to || from === to) return;

      if (!nodeMap.has(from)) {
        nodeMap.set(from, {
          id: from,
          label: e.fromLabel || from,
          shortLabel: formatShortLabel(e.fromLabel || from),
        });
      }
      if (!nodeMap.has(to)) {
        nodeMap.set(to, {
          id: to,
          label: e.toLabel || to,
          shortLabel: formatShortLabel(e.toLabel || to),
        });
      }

      const normEdge = {
        ...e,
        id: e.id ?? `${from}->${to}-${idx}`,
        from,
        to,
      };
      if (e.isRejectedCycle) {
        rejectedEdges.push(normEdge);
      } else {
        validEdges.push(normEdge);
      }
    });

    const nodeList = Array.from(nodeMap.values());

    // Compute in/out adjacency, degree, topological rank, and connected component cluster
    const inAdj = new Map();
    const outAdj = new Map();
    const undirAdj = new Map();
    nodeList.forEach((n) => {
      inAdj.set(n.id, []);
      outAdj.set(n.id, []);
      undirAdj.set(n.id, new Set());
    });

    validEdges.forEach((e) => {
      outAdj.get(e.from)?.push(e.to);
      inAdj.get(e.to)?.push(e.from);
      undirAdj.get(e.from)?.add(e.to);
      undirAdj.get(e.to)?.add(e.from);
    });

    // Connected components for cluster color & radial grouping
    const clusterOf = new Map();
    let clusterIdx = 0;
    nodeList.forEach((n) => {
      if (clusterOf.has(n.id)) return;
      const queue = [n.id];
      clusterOf.set(n.id, clusterIdx);
      while (queue.length > 0) {
        const cur = queue.shift();
        for (const nb of undirAdj.get(cur) || []) {
          if (!clusterOf.has(nb)) {
            clusterOf.set(nb, clusterIdx);
            queue.push(nb);
          }
        }
      }
      clusterIdx++;
    });

    // Longest-path DAG depth
    const inDeg = new Map();
    const depth = new Map();
    nodeList.forEach((n) => {
      inDeg.set(n.id, inAdj.get(n.id).length);
      depth.set(n.id, 0);
    });

    const topoQueue = nodeList.filter((n) => inDeg.get(n.id) === 0).map((n) => n.id);
    const seen = new Set();
    while (topoQueue.length > 0) {
      const u = topoQueue.shift();
      seen.add(u);
      const uDepth = depth.get(u) || 0;
      for (const v of outAdj.get(u) || []) {
        if (depth.get(v) < uDepth + 1) {
          depth.set(v, uDepth + 1);
        }
        inDeg.set(v, inDeg.get(v) - 1);
        if (inDeg.get(v) === 0) {
          topoQueue.push(v);
        }
      }
    }

    const maxDepth = Math.max(1, ...Array.from(depth.values()));

    const enrichedNodes = nodeList.map((n) => {
      const inCount = inAdj.get(n.id).length;
      const outCount = outAdj.get(n.id).length;
      const degree = inCount + outCount;
      const cluster = n.group != null ? Number(n.group) : clusterOf.get(n.id) || 0;

      // Radius scaled proportionally by hub centrality like Gephi network graphs
      const radius = 15 + Math.min(18, degree * 3.4 + outCount * 1.4);

      let palette;
      if (mode === 'mastery') {
        if (n.isRootBlocker) {
          palette = { fill: '#FB7185', stroke: '#E11D48', edge: '#E11D48', status: 'Root Blocker' };
        } else if (n.mastery != null && n.mastery < 0.5) {
          palette = { fill: '#F87171', stroke: '#DC2626', edge: '#EF4444', status: 'Weak Concept' };
        } else if (n.mastery != null && n.mastery < 0.7) {
          palette = { fill: '#FACC15', stroke: '#CA8A04', edge: '#EAB308', status: 'Developing' };
        } else if (n.mastery != null && n.mastery >= 0.7) {
          palette = { fill: '#4ADE80', stroke: '#16A34A', edge: '#22C55E', status: 'Mastered' };
        } else {
          palette = { fill: '#818CF8', stroke: '#4F46E5', edge: '#6366F1', status: 'Syllabus Concept' };
        }
      } else {
        // Group color mixes cluster & depth when single cluster so small DAGs still show multi-hue distinction
        const colorIndex = clusterIdx <= 1 && nodeList.length <= 8
          ? (depth.get(n.id) || 0) % CLUSTER_PALETTE.length
          : cluster % CLUSTER_PALETTE.length;
        palette = CLUSTER_PALETTE[colorIndex];
      }

      return {
        ...n,
        inCount,
        outCount,
        degree,
        cluster,
        depth: depth.get(n.id) || 0,
        radius,
        palette,
      };
    });

    return {
      nodes: enrichedNodes,
      validEdges,
      rejectedEdges,
      inAdj,
      outAdj,
      maxDepth,
      clusterCount: clusterIdx,
    };
  }, [nodes, edges, mode]);

  // Compute deterministic Force-Directed or Layered DAG positions
  const computedPositions = useMemo(() => {
    const list = graphData.nodes;
    const pos = {};
    if (list.length === 0) return pos;

    if (layoutMode === 'dag') {
      // Grouped by topological depth layer
      const layers = new Map();
      list.forEach((n) => {
        if (!layers.has(n.depth)) layers.set(n.depth, []);
        layers.get(n.depth).push(n);
      });
      const layerKeys = Array.from(layers.keys()).sort((a, b) => a - b);
      const padX = 110;
      const spanX = VIEW_W - padX * 2;

      layerKeys.forEach((d, li) => {
        const items = layers.get(d);
        const x = layerKeys.length === 1 ? VIEW_W / 2 : padX + (li / (layerKeys.length - 1)) * spanX;
        const stepY = VIEW_H / (items.length + 1);
        items.forEach((n, idx) => {
          // Gentle vertical wave to keep chords gracefully curved
          const jitterX = items.length > 2 ? (idx % 2 === 0 ? -18 : 18) : 0;
          pos[n.id] = { x: x + jitterX, y: stepY * (idx + 1) };
        });
      });
      return pos;
    }

    // Force-Directed Clustered Network Layout (Gephi style)
    if (list.length === 1) {
      pos[list[0].id] = { x: VIEW_W / 2, y: VIEW_H / 2 };
      return pos;
    }

    // For tiny 2-5 node graphs without clutter, seed in balanced organic polygon with depth skew
    if (list.length <= 5 && graphData.validEdges.length <= 6) {
      const cx = VIEW_W / 2;
      const cy = VIEW_H / 2;
      const rx = 270;
      const ry = 145;
      list.forEach((n, i) => {
        const t = (i / list.length) * Math.PI * 2 - Math.PI * 0.78;
        const depthBias = ((n.depth / Math.max(1, graphData.maxDepth)) - 0.5) * 140;
        pos[n.id] = {
          x: cx + Math.cos(t) * rx * 0.65 + depthBias,
          y: cy + Math.sin(t) * ry,
        };
      });
    } else {
      // Initial deterministic clustered seeding on golden spiral
      const clusterCenters = {};
      const cCount = Math.max(1, graphData.clusterCount);
      for (let c = 0; c < cCount; c++) {
        const angle = (c / cCount) * Math.PI * 2;
        const radiusSpread = cCount === 1 ? 0 : 140;
        clusterCenters[c] = {
          x: VIEW_W / 2 + Math.cos(angle) * radiusSpread,
          y: VIEW_H / 2 + Math.sin(angle) * radiusSpread * 0.72,
        };
      }

      list.forEach((n, i) => {
        const center = clusterCenters[n.cluster] || { x: VIEW_W / 2, y: VIEW_H / 2 };
        const angle = hashStr(n.id + '_a') * Math.PI * 2 + i * 0.6;
        const dist = 60 + hashStr(n.id + '_d') * 140;
        const depthOffset = ((n.depth / Math.max(1, graphData.maxDepth)) - 0.5) * 200;
        pos[n.id] = {
          x: center.x + Math.cos(angle) * dist + depthOffset * 0.45,
          y: center.y + Math.sin(angle) * dist,
        };
      });
    }

    // Fruchterman-Reingold spring simulation
    const k = Math.sqrt((VIEW_W * VIEW_H) / Math.max(4, list.length)) * 0.92;
    const iterations = list.length <= 6 ? 120 : 180;
    const disp = {};
    list.forEach((n) => {
      disp[n.id] = { x: 0, y: 0 };
    });

    for (let iter = 0; iter < iterations; iter++) {
      const temp = 42 * (1 - iter / iterations) + 1.5;

      list.forEach((n) => {
        disp[n.id].x = 0;
        disp[n.id].y = 0;
      });

      // Pairwise repulsion
      for (let i = 0; i < list.length; i++) {
        for (let j = i + 1; j < list.length; j++) {
          const u = list[i];
          const v = list[j];
          let dx = pos[u.id].x - pos[v.id].x;
          let dy = pos[u.id].y - pos[v.id].y;
          let dist = Math.hypot(dx, dy);
          if (dist < 0.01) {
            dx = 1;
            dy = 0.5;
            dist = 1.12;
          }
          const minSep = u.radius + v.radius + 54;
          const force = (k * k) / dist + (dist < minSep ? (minSep - dist) * 2.2 : 0);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          disp[u.id].x += fx;
          disp[u.id].y += fy;
          disp[v.id].x -= fx;
          disp[v.id].y -= fy;
        }
      }

      // Edge spring attraction
      graphData.validEdges.forEach((e) => {
        const pu = pos[e.from];
        const pv = pos[e.to];
        if (!pu || !pv) return;
        const dx = pv.x - pu.x;
        const dy = pv.y - pu.y;
        const dist = Math.hypot(dx, dy) || 0.01;
        const targetDist = 140;
        const force = ((dist - targetDist) * dist) / (k * 1.15);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        disp[e.from].x += fx;
        disp[e.from].y += fy;
        disp[e.to].x -= fx;
        disp[e.to].y -= fy;
      });

      // Gentle gravity toward center + topological left-to-right drift
      list.forEach((n) => {
        const targetX =
          graphData.maxDepth > 0
            ? 140 + (n.depth / graphData.maxDepth) * (VIEW_W - 280)
            : VIEW_W / 2;
        disp[n.id].x += (VIEW_W / 2 - pos[n.id].x) * 0.04 + (targetX - pos[n.id].x) * 0.055;
        disp[n.id].y += (VIEW_H / 2 - pos[n.id].y) * 0.065;
      });

      // Apply displacement bounded by temperature and viewport margins
      list.forEach((n) => {
        const d = disp[n.id];
        const dLen = Math.hypot(d.x, d.y) || 0.01;
        const step = Math.min(dLen, temp);
        pos[n.id].x = Math.max(85, Math.min(VIEW_W - 85, pos[n.id].x + (d.x / dLen) * step));
        pos[n.id].y = Math.max(62, Math.min(VIEW_H - 68, pos[n.id].y + (d.y / dLen) * step));
      });
    }

    return pos;
  }, [graphData, layoutMode]);

  const positions = useMemo(() => {
    const merged = {};
    graphData.nodes.forEach((n) => {
      merged[n.id] = customPos[n.id] || computedPositions[n.id] || { x: VIEW_W / 2, y: VIEW_H / 2 };
    });
    return merged;
  }, [graphData.nodes, computedPositions, customPos]);

  const activeId = hoveredId || selectedId;

  const activeNeighborhood = useMemo(() => {
    if (!activeId) return null;
    const preds = new Set(graphData.inAdj.get(activeId) || []);
    const succs = new Set(graphData.outAdj.get(activeId) || []);
    const relatedNodes = new Set([activeId, ...preds, ...succs]);
    return { preds, succs, relatedNodes };
  }, [activeId, graphData]);

  const inspectedNode = useMemo(() => {
    const targetId = selectedId || hoveredId;
    if (!targetId) return null;
    return graphData.nodes.find((n) => n.id === targetId) || null;
  }, [selectedId, hoveredId, graphData.nodes]);

  const allDisplayedEdges = useMemo(() => {
    const base = [...graphData.validEdges];
    if (showRejectedCycles) {
      base.push(...graphData.rejectedEdges);
    }
    return base;
  }, [graphData.validEdges, graphData.rejectedEdges, showRejectedCycles]);

  // Unique stroke colors needed for SVG arrowhead markers
  const markerPalette = useMemo(() => {
    const colors = new Set(['#3B82F6', '#8B5CF6', '#22C55E', '#EAB308', '#EC4899', '#EF4444', '#14B8A6', '#6366F1', '#E11D48', '#94A3B8']);
    graphData.nodes.forEach((n) => colors.add(n.palette.edge));
    return Array.from(colors);
  }, [graphData.nodes]);

  const colorToMarkerId = (hex) => `${uid}-arrow-${hex.replace('#', '')}`;

  const toSvgDelta = (dxPx, dyPx) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0) return { dx: dxPx, dy: dyPx };
    const scaleX = (VIEW_W / zoom) / rect.width;
    const scaleY = (VIEW_H / zoom) / rect.height;
    return { dx: dxPx * scaleX, dy: dyPx * scaleY };
  };

  const handlePointerMove = (e) => {
    if (!dragState) return;
    const dxPx = e.clientX - dragState.startX;
    const dyPx = e.clientY - dragState.startY;
    const movedEnough = Math.hypot(dxPx, dyPx) > 4;
    const { dx, dy } = toSvgDelta(dxPx, dyPx);

    if (dragState.type === 'node') {
      if (movedEnough && !dragState.moved) {
        setDragState((prev) => ({ ...prev, moved: true }));
      }
      setCustomPos((prev) => ({
        ...prev,
        [dragState.id]: {
          x: Math.max(45, Math.min(VIEW_W - 45, dragState.origX + dx)),
          y: Math.max(45, Math.min(VIEW_H - 45, dragState.origY + dy)),
        },
      }));
    } else if (dragState.type === 'pan') {
      if (movedEnough && !dragState.moved) {
        setDragState((prev) => ({ ...prev, moved: true }));
      }
      setPan({ x: dragState.origX - dx, y: dragState.origY - dy });
    }
  };

  const handlePointerUp = () => {
    if (dragState?.type === 'node' && !dragState.moved) {
      setSelectedId((prev) => (prev === dragState.id ? null : dragState.id));
    } else if (dragState?.type === 'pan' && !dragState.moved) {
      setSelectedId(null);
    }
    setDragState(null);
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setCustomPos({});
    setSelectedId(null);
  };

  if (graphData.nodes.length === 0) {
    return (
      <div className="p-6 rounded-2xl bg-white border border-slate-200 text-center text-sm text-slate-500">
        No prerequisite concepts available to graph yet.
      </div>
    );
  }

  // Compute zoomed & panned viewBox
  const vbW = VIEW_W / zoom;
  const vbH = VIEW_H / zoom;
  const vbX = (VIEW_W - vbW) / 2 + pan.x;
  const vbY = (VIEW_H - vbH) / 2 + pan.y;

  const nodeLookup = new Map(graphData.nodes.map((n) => [n.id, n]));

  return (
    <div className="rounded-2xl bg-white border border-slate-200 shadow-sm overflow-hidden">
      {/* Toolbar Header */}
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/80 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Network className="w-4 h-4 text-indigo-600" />
            <h4 className="text-sm font-black text-slate-900">{title}</h4>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-700">
              {graphData.nodes.length} Nodes &bull; {graphData.validEdges.length} Directed Edges
            </span>
          </div>
          {subtitle && <p className="text-[11px] text-slate-500 mt-0.5">{subtitle}</p>}
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {/* Layout Switcher */}
          <div className="inline-flex rounded-xl bg-slate-200/70 p-0.5 text-[11px] font-bold">
            <button
              type="button"
              onClick={() => { setLayoutMode('network'); setCustomPos({}); }}
              className={`px-2.5 py-1 rounded-lg transition-colors flex items-center gap-1 ${
                layoutMode === 'network' ? 'bg-white text-indigo-700 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Network className="w-3 h-3" /> Network Graph
            </button>
            <button
              type="button"
              onClick={() => { setLayoutMode('dag'); setCustomPos({}); }}
              className={`px-2.5 py-1 rounded-lg transition-colors flex items-center gap-1 ${
                layoutMode === 'dag' ? 'bg-white text-indigo-700 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <GitBranch className="w-3 h-3" /> DAG Layers
            </button>
          </div>

          {graphData.rejectedEdges.length > 0 && (
            <button
              type="button"
              onClick={() => setShowRejectedCycles((v) => !v)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-bold border transition-colors flex items-center gap-1 ${
                showRejectedCycles
                  ? 'bg-rose-50 border-rose-200 text-rose-700'
                  : 'bg-white border-slate-200 text-slate-500'
              }`}
            >
              <AlertTriangle className="w-3 h-3" />
              {showRejectedCycles ? 'Hide Cycle Pruning' : `Show Cycle (${graphData.rejectedEdges.length})`}
            </button>
          )}

          {/* Zoom Controls */}
          <div className="inline-flex items-center rounded-xl border border-slate-200 bg-white overflow-hidden">
            <button
              type="button"
              onClick={() => setZoom((z) => Math.max(0.65, Number((z - 0.15).toFixed(2))))}
              className="p-1.5 text-slate-600 hover:bg-slate-100"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="px-1.5 text-[10px] font-mono font-bold text-slate-600 border-x border-slate-100">
              {Math.round(zoom * 100)}%
            </span>
            <button
              type="button"
              onClick={() => setZoom((z) => Math.min(2.0, Number((z + 0.15).toFixed(2))))}
              className="p-1.5 text-slate-600 hover:bg-slate-100"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={resetView}
              className="p-1.5 text-slate-600 hover:bg-slate-100 border-l border-slate-100"
              title="Reset Graph Layout & Zoom"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Graph SVG Canvas */}
      <div
        className="relative bg-white select-none"
        style={{ height: `${height}px` }}
      >
        {/* Subtle dot grid matching interactive visualization feel */}
        <div
          className="absolute inset-0 pointer-events-none opacity-45"
          style={{
            backgroundImage: 'radial-gradient(#CBD5E1 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}
        />

        <svg
          ref={svgRef}
          viewBox={`${vbX} ${vbY} ${vbW} ${vbH}`}
          className={`w-full h-full relative z-10 ${dragState?.type === 'pan' ? 'cursor-grabbing' : 'cursor-grab'}`}
          onPointerDown={(e) => {
            if (e.target === svgRef.current) {
              setDragState({
                type: 'pan',
                startX: e.clientX,
                startY: e.clientY,
                origX: pan.x,
                origY: pan.y,
                moved: false,
              });
            }
          }}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
        >
          <defs>
            <filter id={`${uid}-node-shadow`} x="-35%" y="-35%" width="170%" height="170%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#0F172A" floodOpacity="0.14" />
            </filter>
            {markerPalette.map((hex) => (
              <marker
                key={hex}
                id={colorToMarkerId(hex)}
                viewBox="0 0 10 10"
                refX="8.5"
                refY="5"
                markerWidth="5.5"
                markerHeight="5.5"
                orient="auto-start-reverse"
              >
                <path d="M 0 1.2 L 9.5 5 L 0 8.8 z" fill={hex} />
              </marker>
            ))}
          </defs>

          {/* 1. Curved Directed Edges */}
          <g>
            {allDisplayedEdges.map((edge) => {
              const p1 = positions[edge.from];
              const p2 = positions[edge.to];
              const uNode = nodeLookup.get(edge.from);
              const vNode = nodeLookup.get(edge.to);
              if (!p1 || !p2 || !uNode || !vNode) return null;

              const dx = p2.x - p1.x;
              const dy = p2.y - p1.y;
              const dist = Math.hypot(dx, dy) || 1;
              const ux = dx / dist;
              const uy = dy / dist;

              // Trim edge cleanly to node boundaries so arrowheads rest on node rim
              const startPad = uNode.radius + 3;
              const endPad = vNode.radius + 7;
              const sx = p1.x + ux * Math.min(startPad, dist * 0.35);
              const sy = p1.y + uy * Math.min(startPad, dist * 0.35);
              const ex = p2.x - ux * Math.min(endPad, dist * 0.35);
              const ey = p2.y - uy * Math.min(endPad, dist * 0.35);

              // Perpendicular arc curvature (stronger sweep for rejected cycle arcs!)
              const midX = (sx + ex) / 2;
              const midY = (sy + ey) / 2;
              const nx = -uy;
              const ny = ux;
              const curveMag = edge.isRejectedCycle
                ? Math.max(68, dist * 0.34)
                : Math.min(44, Math.max(18, dist * 0.14));
              const cx = midX + nx * curveMag;
              const cy = midY + ny * curveMag;

              const isRelated =
                !activeNeighborhood ||
                (!edge.isRejectedCycle && (edge.from === activeId || edge.to === activeId));

              const edgeColor = edge.isRejectedCycle
                ? REJECTED_STYLE.edge
                : uNode.palette.edge;

              const strokeWidth = edge.isRejectedCycle
                ? 2.2
                : activeNeighborhood && (edge.from === activeId || edge.to === activeId)
                ? 3.2
                : 1.9 + Math.min(1.6, ((edge.confidence || 0.85) - 0.5) * 2.2);

              // Quadratic curve midpoint B(0.5) = 0.25*S + 0.5*C + 0.25*E
              const labelX = 0.25 * sx + 0.5 * cx + 0.25 * ex;
              const labelY = 0.25 * sy + 0.5 * cy + 0.25 * ey;

              return (
                <g
                  key={edge.id}
                  style={{
                    opacity: isRelated ? (edge.isRejectedCycle ? 0.92 : 0.82) : 0.14,
                    transition: 'opacity 160ms ease',
                  }}
                >
                  <path
                    d={`M ${sx} ${sy} Q ${cx} ${cy} ${ex} ${ey}`}
                    fill="none"
                    stroke={edgeColor}
                    strokeWidth={strokeWidth}
                    strokeDasharray={edge.isRejectedCycle ? '6 4' : undefined}
                    strokeLinecap="round"
                    markerEnd={`url(#${colorToMarkerId(edgeColor)})`}
                  >
                    <title>
                      {`${uNode.label} → ${vNode.label}${edge.reasoning ? ` (${edge.reasoning})` : ''}`}
                    </title>
                  </path>

                  {edge.isRejectedCycle && (
                    <g transform={`translate(${labelX}, ${labelY})`}>
                      <rect
                        x="-42"
                        y="-10"
                        width="84"
                        height="20"
                        rx="10"
                        fill="#FFF1F2"
                        stroke="#E11D48"
                        strokeWidth="1.2"
                      />
                      <text
                        x="0"
                        y="3.5"
                        textAnchor="middle"
                        fontSize="8.5"
                        fontWeight="800"
                        fill="#BE123C"
                      >
                        CYCLE PRUNED
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </g>

          {/* 2. Circular Network Nodes & Labels */}
          <g>
            {graphData.nodes.map((node) => {
              const p = positions[node.id];
              if (!p) return null;

              const isSelected = selectedId === node.id;
              const isHovered = hoveredId === node.id;
              const isInNeighborhood =
                !activeNeighborhood || activeNeighborhood.relatedNodes.has(node.id);

              const r = node.radius;

              return (
                <g
                  key={node.id}
                  transform={`translate(${p.x}, ${p.y})`}
                  style={{
                    opacity: isInNeighborhood ? 1 : 0.22,
                    cursor: dragState?.type === 'node' ? 'grabbing' : 'pointer',
                    transition: 'opacity 160ms ease',
                  }}
                  onPointerEnter={() => setHoveredId(node.id)}
                  onPointerLeave={() => setHoveredId((prev) => (prev === node.id ? null : prev))}
                  onPointerDown={(e) => {
                    e.stopPropagation();
                    setDragState({
                      type: 'node',
                      id: node.id,
                      startX: e.clientX,
                      startY: e.clientY,
                      origX: p.x,
                      origY: p.y,
                      moved: false,
                    });
                  }}
                >
                  <title>{node.label}</title>

                  {/* Root Blocker / Selected Glow Halo */}
                  {(node.isRootBlocker || isSelected || isHovered) && (
                    <circle
                      r={r + 7}
                      fill="none"
                      stroke={node.palette.stroke}
                      strokeWidth={isSelected ? 2.5 : 1.8}
                      strokeDasharray={node.isRootBlocker && !isSelected ? '4 3' : undefined}
                      opacity={isSelected ? 0.65 : 0.4}
                    />
                  )}

                  {/* Main Gephi-style Circle */}
                  <circle
                    r={r}
                    fill={node.palette.fill}
                    stroke={isSelected ? '#0F172A' : node.palette.stroke}
                    strokeWidth={isSelected ? 3 : 2.2}
                    filter={`url(#${uid}-node-shadow)`}
                  />

                  {/* Mastery Percentage or Step Number Inside Node */}
                  {mode === 'mastery' && node.mastery != null ? (
                    <text
                      x="0"
                      y="4"
                      textAnchor="middle"
                      fontSize={r >= 22 ? '11' : '9.5'}
                      fontWeight="900"
                      fill="#0F172A"
                      pointerEvents="none"
                    >
                      {Math.round(node.mastery * 100)}%
                    </text>
                  ) : (
                    <circle r={Math.max(3, r * 0.26)} fill="white" opacity="0.55" pointerEvents="none" />
                  )}

                  {/* Crisp Haloed Concept Label */}
                  <text
                    x="0"
                    y={r + 14}
                    textAnchor="middle"
                    fontSize={r >= 22 ? '11.5' : '10.5'}
                    fontWeight="800"
                    fill="#0F172A"
                    pointerEvents="none"
                    style={{
                      paintOrder: 'stroke',
                      stroke: '#FFFFFF',
                      strokeWidth: '4px',
                      strokeLinejoin: 'round',
                    }}
                  >
                    {node.shortLabel}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        {/* Floating Legend Pill */}
        <div className="absolute bottom-3 left-3 z-20 flex flex-wrap items-center gap-2 px-3 py-1.5 rounded-xl bg-white/90 backdrop-blur-xs border border-slate-200 shadow-xs text-[10px] font-bold text-slate-600 pointer-events-none">
          {mode === 'mastery' ? (
            <>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#FB7185] border border-[#E11D48]" /> Root Blocker</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#F87171] border border-[#DC2626]" /> Weak (&lt;50%)</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#FACC15] border border-[#CA8A04]" /> Developing (50–69%)</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#4ADE80] border border-[#16A34A]" /> Mastered (&ge;70%)</span>
            </>
          ) : (
            <>
              <span className="flex items-center gap-1"><ArrowRight className="w-3 h-3 text-indigo-600" /> Prerequisite A &rarr; B</span>
              <span>&bull; Node Size = Hub Connections</span>
              {graphData.rejectedEdges.length > 0 && (
                <span className="text-rose-600 font-black">&bull; Dashed Red = Pruned Cycle</span>
              )}
            </>
          )}
        </div>
      </div>

      {/* Interactive Node Inspector Strip */}
      <div className="px-4 py-3 border-t border-slate-100 bg-slate-50/70">
        {inspectedNode ? (
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className="w-3 h-3 rounded-full inline-block border"
                  style={{
                    backgroundColor: inspectedNode.palette.fill,
                    borderColor: inspectedNode.palette.stroke,
                  }}
                />
                <span className="text-xs font-black text-slate-900">{inspectedNode.label}</span>
                {inspectedNode.isRootBlocker && (
                  <span className="px-2 py-0.5 rounded-md text-[10px] font-black uppercase bg-rose-100 text-rose-700 border border-rose-200">
                    Root Blocker
                  </span>
                )}
                {inspectedNode.mastery != null && (
                  <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-white border border-slate-200 text-slate-700">
                    Mastery: {Math.round(inspectedNode.mastery * 100)}%
                  </span>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-600">
                <span>
                  <strong className="text-slate-700">Requires ({inspectedNode.inCount}):</strong>{' '}
                  {(graphData.inAdj.get(inspectedNode.id) || [])
                    .map((id) => nodeLookup.get(id)?.shortLabel || id)
                    .join(', ') || 'None (Foundational Root)'}
                </span>
                <span>
                  <strong className="text-indigo-700">Unlocks ({inspectedNode.outCount}):</strong>{' '}
                  {(graphData.outAdj.get(inspectedNode.id) || [])
                    .map((id) => nodeLookup.get(id)?.shortLabel || id)
                    .join(', ') || 'Terminal Concept'}
                </span>
              </div>
              {inspectedNode.description && (
                <p className="text-[11px] text-slate-500">{inspectedNode.description}</p>
              )}
            </div>

            {onNodeAction && inspectedNode.conceptId && (
              <button
                type="button"
                onClick={() => onNodeAction(inspectedNode.conceptId)}
                disabled={actionDisabled}
                className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 self-start sm:self-auto disabled:opacity-50"
              >
                <Sparkles className="w-3.5 h-3.5" />
                {actionLabel}
              </button>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span className="flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-indigo-500" />
              Hover or click any concept node to highlight prerequisites &amp; dependencies, or drag nodes to rearrange.
            </span>
            <span className="hidden sm:inline font-mono text-[10px]">Drag background to pan</span>
          </div>
        )}
      </div>
    </div>
  );
}
