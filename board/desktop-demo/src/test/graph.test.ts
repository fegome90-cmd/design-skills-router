
import { readFileSync } from "node:fs"
import { describe, expect, test } from "vitest"
import graph from "../../../../release/design-router-mapa-fuentes.json"
import { directedRelations, flowNeighbourLimit, flowProjection, nodes, projectFlow, relationKindLabel, relationKindLabels, relationsFor, splitRelations, type GraphNode } from "@/graph"

const edges = graph.edges as { from: string; to: string; kind: string; condition: string }[]
const itemEdges = (side: ReturnType<typeof flowProjection>["incoming"]) => side.items.flatMap(item => item.edges)

describe("node flow projection", () => {
  test("keeps every relation of every node, drawn alone or bundled", () => {
    for (const id of nodes.keys()) {
      const flow = flowProjection(id)
      const drawn = [...itemEdges(flow.incoming), ...itemEdges(flow.outgoing)]
      expect(drawn).toHaveLength(relationsFor(id).length)
      expect(new Set(drawn).size).toBe(drawn.length)
      expect(flow.incoming.edgeCount + flow.outgoing.edgeCount).toBe(drawn.length)
      for (const side of [flow.incoming, flow.outgoing]) {
        expect(side.bundled).toBe(side.neighbourCount > flowNeighbourLimit)
      }
    }
  })

  test("bundles a hub by kind and neighbour group", () => {
    const flow = flowProjection("py-runner-show-node")
    expect(flow.incoming.bundled).toBe(true)
    expect(flow.incoming.edgeCount).toBe(212)
    expect(flow.incoming.items.length).toBeLessThanOrEqual(flowNeighbourLimit)
    for (const item of flow.incoming.items) {
      expect(item.type).toBe("bundle")
      if (item.type === "bundle") {
        for (const edge of item.edges) {
          expect(edge.kind).toBe(item.kind)
          expect(nodes.get(edge.from)!.group).toBe(item.group)
        }
      }
    }
  })

  test("projects fixture edges and nodes without reading the released graph", () => {
    const node = (id: string, group: string): GraphNode => ({ id, title: id, group, path: "", symbol: "", summary: "", source: "" })
    const focus = node("fixture-focus", "focus")
    const a = node("fixture-a", "fixtures")
    const b = node("fixture-b", "fixtures")
    const fixture = new Map([focus, a, b].map(value => [value.id, value]))
    const fixtureEdges = [
      { from: a.id, to: focus.id, kind: "requires", condition: "first" },
      { from: a.id, to: focus.id, kind: "requires", condition: "parallel" },
      { from: b.id, to: focus.id, kind: "requires", condition: "third" },
      { from: focus.id, to: a.id, kind: "alternative", condition: "" },
    ]

    const flow = projectFlow(focus, fixtureEdges, id => fixture.get(id)!, 1)
    expect(flow.focus).toBe(focus)
    expect(flow.incoming).toMatchObject({ bundled: true, neighbourCount: 2, edgeCount: 3 })
    expect(flow.incoming.items).toMatchObject([{ type: "bundle", kind: "requires", group: a.group, edges: fixtureEdges.slice(0, 3) }])
    expect(flow.outgoing).toMatchObject({ bundled: false, neighbourCount: 1, edgeCount: 1 })
    expect(flow.outgoing.items).toMatchObject([{ type: "node", node: a, edges: fixtureEdges.slice(3) }])
  })

  test("keeps parallel relations between the same pair", () => {
    const pairs = new Map<string, number>()
    for (const edge of edges) pairs.set(`${edge.from}\u0000${edge.to}`, (pairs.get(`${edge.from}\u0000${edge.to}`) ?? 0) + 1)
    const [pair] = [...pairs].find(([, count]) => count > 1)!
    const [from, to] = pair.split("\u0000")
    const flow = flowProjection(from)
    const parallel = itemEdges(flow.outgoing).filter(edge => edge.to === to)
    expect(parallel).toHaveLength(2)
  })
})

describe("relation labels", () => {
  test("match the v1.3 generator dictionary", () => {
    const source = readFileSync("../../map/assemble_map.py", "utf8")
    const dictionary = source.match(/label\s*=\s*\{([^}]*)\}\s*\[\s*e\[\s*'kind'\s*\]\s*\]/)
    expect(dictionary, "map/assemble_map.py no longer has the label dictionary").not.toBeNull()
    const pairs = Object.fromEntries([...dictionary![1].matchAll(/'([^']+)'\s*:\s*'([^']+)'/g)].map(match => [match[1], match[2]]))
    expect(relationKindLabels).toEqual(pairs)
  })

  test("translate the internal keys and leave Spanish kinds unchanged", () => {
    for (const kind of new Set(edges.map(edge => edge.kind))) {
      expect(relationKindLabel(kind)).toBe(relationKindLabels[kind] ?? kind)
      expect(relationKindLabel(kind)).not.toMatch(/^(alternative|all_branch|template_ref|requires)$/)
    }
    expect(relationKindLabel("ubicación")).toBe("ubicación")
    expect(relationKindLabel("all_branch")).toBe("Rama obligatoria")
  })
})

describe("directed relations", () => {
  test("splits a hub by direction without changing JSON order", () => {
    const id = "py-runner-show-node"
    const r = directedRelations(id)
    expect([r.outgoing.length, r.incoming.length]).toEqual([7, 212])
    expect([r.pythonOutgoing.length, r.pythonIncoming.length]).toEqual([0, 0])
    expect(r.outgoing.map(row => row.edge)).toEqual(edges.filter(edge => edge.from === id))
    expect(r.incoming.map(row => row.edge)).toEqual(edges.filter(edge => edge.to === id))
  })

  test("Q00 separates Python code like v1.3", () => {
    const r = directedRelations("Q00")
    expect([r.pythonOutgoing.length, r.pythonIncoming.length]).toEqual([0, 2])
    expect([r.outgoing.length, r.incoming.length]).toEqual([5, 3])
    const general = new Set(r.incoming.map(row => row.edge))
    expect(r.pythonIncoming.every(row => !general.has(row.edge))).toBe(true)
  })

  test("detects Python by extension, case-insensitive, on both sides", () => {
    const node = (id: string, path: string): GraphNode => ({ id, path, title: id, group: "g", symbol: "", summary: "", source: "" })
    const fixture = new Map([["Q", node("Q", "a.md")], ["A", node("A", "x.PY")], ["B", node("B", "y.ts")]])
    const fixtureEdges = [
      { from: "Q", to: "A", kind: "k", condition: "" },
      { from: "B", to: "Q", kind: "k", condition: "" },
      { from: "A", to: "Q", kind: "k", condition: "" },
    ]
    const r = splitRelations("Q", fixtureEdges, id => fixture.get(id)!, true)
    expect(r.pythonOutgoing.map(row => row.other.id)).toEqual(["A"])
    expect(r.pythonIncoming.map(row => row.other.id)).toEqual(["A"])
    expect(r.incoming.map(row => row.other.id)).toEqual(["B"])
    expect(r.outgoing).toEqual([])
  })
})
