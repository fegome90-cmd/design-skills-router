import graph from "../../../release/design-router-mapa-fuentes.json"

export type GraphNode = {
  id: string
  title: string
  group: string
  path: string
  symbol: string
  summary: string
  source: string
  line?: number
  aliases?: string[]
}

export type GraphEdge = { from: string; to: string; kind: string; condition: string }

const graphNodes = graph.nodes as GraphNode[]
const graphEdges = graph.edges as GraphEdge[]

export const rootNodeId: string = graph.root
export const nodes = new Map(graphNodes.map(node => [node.id, node]))
export const nodeGroups = [...new Set(graphNodes.map(node => node.group))].sort((a, b) => a.localeCompare(b, "es"))

export const nodeHashPrefix = "#router-node-"

const normalize = (value: string) => value.normalize("NFD").replace(/\p{M}/gu, "").toLocaleLowerCase("es")

const searchableNodes = graphNodes.map(node => ({
  node,
  text: normalize([node.id, node.title, node.group, node.path, node.symbol, ...(node.aliases ?? [])].join(" ")),
}))

export function nodeHref(id: string) {
  return nodeHashPrefix + encodeURIComponent(id)
}

export function readNodeId(hash: string) {
  if (!hash.startsWith(nodeHashPrefix)) return rootNodeId
  try {
    const id = decodeURIComponent(hash.slice(nodeHashPrefix.length))
    return nodes.has(id) ? id : rootNodeId
  } catch {
    return rootNodeId
  }
}

export function findNodes(query: string, group: string) {
  const terms = normalize(query).trim().split(/\s+/).filter(Boolean)
  return searchableNodes
    .filter(({ node, text }) => (!group || node.group === group) && terms.every(term => text.includes(term)))
    .map(({ node }) => node)
}

export function relationsFor(id: string) {
  return graphEdges
    .filter(edge => edge.from === id || edge.to === id)
    .map(edge => ({ edge, other: nodes.get(edge.from === id ? edge.to : edge.from)! }))
}

/** Spanish labels for internal relation kinds, matching map/assemble_map.py. */
export const relationKindLabels: Record<string, string> = {
  alternative: "Alternativa",
  all_branch: "Rama obligatoria",
  template_ref: "Expande plantilla",
  requires: "Prerrequisito",
}

export function relationKindLabel(kind: string) {
  return Object.hasOwn(relationKindLabels, kind) ? relationKindLabels[kind] : kind
}

export type Relation = { edge: GraphEdge; other: GraphNode }
export type DirectedRelations = {
  outgoing: Relation[]
  incoming: Relation[]
  pythonOutgoing: Relation[]
  pythonIncoming: Relation[]
}

/** Keep JSON order and optionally separate Python code as in map/view.py. */
export function splitRelations(
  id: string, edges: readonly GraphEdge[], nodeOf: (id: string) => GraphNode, splitPython: boolean,
): DirectedRelations {
  const result: DirectedRelations = { outgoing: [], incoming: [], pythonOutgoing: [], pythonIncoming: [] }
  const isPython = (node: GraphNode) => splitPython && /\.py$/i.test(node.path ?? "")
  for (const edge of edges) {
    if (edge.from === id) {
      const other = nodeOf(edge.to)
      const section = isPython(other) ? result.pythonOutgoing : result.outgoing
      section.push({ edge, other })
    }
    if (edge.to === id) {
      const other = nodeOf(edge.from)
      const section = isPython(other) ? result.pythonIncoming : result.incoming
      section.push({ edge, other })
    }
  }
  return result
}

export function directedRelations(id: string) {
  return splitRelations(id, graphEdges, other => nodes.get(other)!, id === "Q00")
}

export function exportGraph() {
  const url = URL.createObjectURL(new Blob([JSON.stringify(graph)], { type: "application/json" }))
  const link = document.createElement("a")
  link.href = url
  link.download = "design-router-mapa-fuentes.json"
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** One entry in a side of the node flow: a single neighbour, or a bundle of relations. */
export type FlowItem =
  | { type: "node"; key: string; node: GraphNode; edges: GraphEdge[] }
  | { type: "bundle"; key: string; kind: string; group: string; edges: GraphEdge[] }

export type FlowSide = {
  items: FlowItem[]
  /** Every relation on this side, whether it is drawn alone or inside a bundle. */
  edgeCount: number
  neighbourCount: number
  bundled: boolean
}

export type FlowProjection = { focus: GraphNode; incoming: FlowSide; outgoing: FlowSide }

/** Above this many distinct neighbours, a side groups its relations by kind and neighbour group. */
export const flowNeighbourLimit = 12

function flowSide(
  edges: GraphEdge[], neighbourOf: (edge: GraphEdge) => string, nodeOf: (id: string) => GraphNode, limit: number,
): FlowSide {
  const byNeighbour = new Map<string, GraphEdge[]>()
  for (const edge of edges) {
    const id = neighbourOf(edge)
    byNeighbour.set(id, [...(byNeighbour.get(id) ?? []), edge])
  }
  if (byNeighbour.size <= limit) {
    const items: FlowItem[] = [...byNeighbour].map(([id, list]) => ({
      type: "node", key: id, node: nodeOf(id), edges: list,
    }))
    items.sort((a, b) => (a.type === "node" && b.type === "node" ? a.node.title.localeCompare(b.node.title, "es") : 0))
    return { items, edgeCount: edges.length, neighbourCount: byNeighbour.size, bundled: false }
  }
  // Parallel edges keep their own entry in the bundle, so no relation is merged away.
  const bundles = new Map<string, { kind: string; group: string; edges: GraphEdge[] }>()
  for (const edge of edges) {
    const group = nodeOf(neighbourOf(edge)).group
    const key = `${edge.kind}\u0000${group}`
    const bundle = bundles.get(key) ?? { kind: edge.kind, group, edges: [] }
    bundle.edges.push(edge)
    bundles.set(key, bundle)
  }
  const items: FlowItem[] = [...bundles]
    .map(([key, bundle]) => ({ type: "bundle" as const, key, ...bundle }))
    .sort((a, b) => b.edges.length - a.edges.length || a.kind.localeCompare(b.kind, "es"))
  return { items, edgeCount: edges.length, neighbourCount: byNeighbour.size, bundled: true }
}

/** Incoming relations, the node and outgoing relations; hubs are bundled, never truncated. */
export function projectFlow(
  focus: GraphNode,
  edges: readonly GraphEdge[],
  nodeOf: (id: string) => GraphNode,
  limit = flowNeighbourLimit,
): FlowProjection {
  return {
    focus,
    incoming: flowSide(edges.filter(edge => edge.to === focus.id), edge => edge.from, nodeOf, limit),
    outgoing: flowSide(edges.filter(edge => edge.from === focus.id), edge => edge.to, nodeOf, limit),
  }
}

export function flowProjection(id: string, limit = flowNeighbourLimit): FlowProjection {
  return projectFlow(nodes.get(id)!, graphEdges, id => nodes.get(id)!, limit)
}
