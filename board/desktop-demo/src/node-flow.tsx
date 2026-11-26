import {
  Dialog, DialogBackdrop, DialogClose, DialogContent, DialogDescription, DialogTitle, DialogTrigger,
} from "@ui-sdk/react/dialog"
import { Toolbar, ToolbarButton } from "@ui-sdk/react/toolbar"
import cytoscape, { type Core, type ElementDefinition, type Position, type StylesheetJson } from "cytoscape"
import { Maximize2, RotateCcw, Scan, X, ZoomIn, ZoomOut } from "lucide-react"
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type RefObject } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { relationKindLabel, type FlowItem, type FlowProjection } from "@/graph"
import { flowColumns, flowPadding, stackRows } from "@/node-flow-layout"

/* Registered canvas exception: React owns the navigation and the full lists. */
type Side = "in" | "out"
type FlowMode = "inline" | "fullscreen"
export type OpenNode = (id: string, options?: { keepFocus?: boolean }) => void
type FlowProps = {
  flow: FlowProjection
  onOpenNode: OpenNode
  onOpenSection: (side: Side) => void
}

const zoomInFactor = 1.25
const zoomOutFactor = 0.8

const minNodeHeight = 38
const rowGap = 14
const labelBounds = {
  includeNodes: false, includeEdges: false, includeLabels: true, includeOverlays: false, includeUnderlays: false,
}

// A 2D context resolves the tokens into colours the canvas renderer can use.
function readTokens(element: HTMLElement) {
  const probe = document.createElement("canvas").getContext("2d")!
  const css = getComputedStyle(element)
  const colour = (name: string) => {
    probe.fillStyle = css.getPropertyValue(name).trim()
    return String(probe.fillStyle)
  }
  return {
    foreground: colour("--foreground"),
    background: colour("--background"),
    card: colour("--card"),
    muted: colour("--muted"),
    mutedForeground: colour("--muted-foreground"),
    ring: colour("--ring"),
    font: css.fontFamily,
  }
}

function stylesheet(tokens: ReturnType<typeof readTokens>): StylesheetJson {
  return [
    {
      selector: "node",
      style: {
        shape: "rectangle",
        width: "data(width)",
        height: "data(height)",
        "background-color": tokens.card,
        "border-width": 1,
        "border-color": tokens.mutedForeground,
        label: "data(label)",
        color: tokens.foreground,
        "font-family": tokens.font,
        "font-size": 13,
        "text-valign": "center",
        "text-halign": "center",
        "text-wrap": "wrap",
        "text-overflow-wrap": "whitespace",
        "text-max-width": "data(textWidth)",
      },
    },
    {
      selector: "node.bundle",
      style: { "background-color": tokens.muted, "border-style": "dashed", "font-size": 12 },
    },
    {
      selector: "node.focus",
      style: {
        "background-color": tokens.foreground,
        "border-color": tokens.foreground,
        color: tokens.background,
        "font-weight": 600,
      },
    },
    {
      selector: "node.kbd-focus",
      style: { "border-width": 3, "border-color": tokens.ring, "z-index": 10 },
    },
    {
      selector: "node.focus.kbd-focus",
      style: {
        "border-color": tokens.background,
        "underlay-color": tokens.ring,
        "underlay-opacity": 1,
        "underlay-padding": 5,
      },
    },
    {
      selector: "edge",
      style: {
        width: 1,
        "curve-style": "straight",
        "source-endpoint": "50% 0%",
        "target-endpoint": "-50% 0%",
        "line-color": tokens.mutedForeground,
        "target-arrow-shape": "triangle",
        "target-arrow-color": tokens.mutedForeground,
        "arrow-scale": 0.8,
      },
    },
    { selector: "edge.bundle", style: { "line-style": "dashed", width: 1.5 } },
  ]
}

// Cytoscape's whitespace wrapper also breaks at a zero-width space.
function withWrapPoints(label: string) {
  return label.replace(/[._/-]/g, "$&\u200b")
}

function relationKinds(edges: FlowItem["edges"]) {
  return [...new Set(edges.map(edge => relationKindLabel(edge.kind)))].join(" · ")
}

function itemLabel(item: FlowItem) {
  if (item.type === "node") return `${item.node.title}\n${relationKinds(item.edges)}`
  return `${item.edges.length} × ${relationKindLabel(item.kind)}\n${item.group}`
}

function relationCount(count: number) {
  return `${count} ${count === 1 ? "relación" : "relaciones"}`
}

function itemAnnouncement(item: FlowItem) {
  return item.type === "node"
    ? `${item.node.title} · ${relationKinds(item.edges)} · ${relationCount(item.edges.length)}`
    : `${item.edges.length} × ${relationKindLabel(item.kind)} · ${item.group} · grupo, Enter abre su lista`
}

function buildElements(flow: FlowProjection, nodeWidth: number) {
  const size = { width: nodeWidth, height: minNodeHeight, textWidth: `${nodeWidth - 20}px` }
  const elements: ElementDefinition[] = [
    { group: "nodes", data: { id: "focus", label: withWrapPoints(flow.focus.title), announcement: `${flow.focus.title} · ${relationCount(flow.incoming.edgeCount + flow.outgoing.edgeCount)}`, ...size }, classes: "focus" },
  ]
  const place = (side: Side, items: FlowItem[]) => {
    for (const item of items) {
      const id = `${side}:${item.key}`
      elements.push({
        group: "nodes",
        data: {
          id, side, label: withWrapPoints(itemLabel(item)), announcement: itemAnnouncement(item),
          target: item.type === "node" ? item.node.id : undefined, ...size,
        },
        classes: item.type,
      }, {
        group: "edges",
        data: {
          id: `edge:${id}`,
          source: side === "in" ? id : "focus",
          target: side === "in" ? "focus" : id,
        },
        classes: item.type,
      })
    }
  }
  place("in", flow.incoming.items)
  place("out", flow.outgoing.items)
  return elements
}

function layoutFlow(instance: Core, element: HTMLDivElement, flow: FlowProjection, nodeWidth: number, columnGap: number, mode: FlowMode) {
  instance.batch(() => {
    instance.elements().remove()
    instance.add(buildElements(flow, nodeWidth))
  })
  // Node label dimensions are independent of the temporary positions.
  const heights = new Map(instance.nodes().map(node => [
    node.id(), Math.max(minNodeHeight, Math.ceil(node.boundingBox(labelBounds).h) + 16),
  ] as const))
  const positions: Record<string, Position> = { focus: { x: 0, y: 0 } }
  for (const side of ["in", "out"] as const) {
    const ids = instance.nodes(`[side = "${side}"]`).map(node => node.id())
    const x = (side === "in" ? -1 : 1) * (nodeWidth + columnGap)
    stackRows(ids.map(id => heights.get(id)!), rowGap).forEach((y, index) => {
      positions[ids[index]] = { x, y }
    })
  }
  instance.batch(() => {
    instance.nodes().forEach(node => { node.data("height", heights.get(node.id())!) })
  })
  instance.layout({ name: "preset", positions, fit: false }).run()
  if (mode === "inline") {
    const bounds = instance.elements().boundingBox({ includeOverlays: false, includeUnderlays: false })
    const extent = Math.max(-bounds.y1, bounds.y2)
    element.style.height = `${Math.max(220, Math.ceil(2 * extent + 2 * flowPadding) + 2)}px`
  }
  instance.resize()
}

function sideSummary(label: string, side: FlowProjection["incoming"]) {
  if (side.edgeCount === 0) return `${label}: ninguna.`
  const relations = relationCount(side.edgeCount)
  const neighbours = `${side.neighbourCount} ${side.neighbourCount === 1 ? "nodo" : "nodos"}`
  return side.bundled
    ? `${label}: ${relations} con ${neighbours}, agrupadas por tipo y grupo.`
    : `${label}: ${relations} con ${neighbours}.`
}

export function flowSummary(flow: FlowProjection) {
  return `${sideSummary("Entradas", flow.incoming)} ${sideSummary("Salidas", flow.outgoing)}`
}

function zoomBy(instance: Core, factor: number) {
  instance.zoom({
    level: instance.zoom() * factor,
    renderedPosition: { x: instance.width() / 2, y: instance.height() / 2 },
  })
}

function resetView(instance: Core) {
  instance.zoom(1)
  instance.center(instance.$id("focus"))
}

function FlowZoomToolbar({ instance }: { instance: Core | null }) {
  return (
    <Toolbar aria-label="Zoom del flujo" className="node-flow-toolbar" disabled={!instance}>
      <ToolbarButton aria-label="Acercar" title="Acercar (+)" onClick={() => instance && zoomBy(instance, zoomInFactor)}>
        <ZoomIn aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton aria-label="Alejar" title="Alejar (-)" onClick={() => instance && zoomBy(instance, zoomOutFactor)}>
        <ZoomOut aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton aria-label="Ajustar" title="Ajustar" onClick={() => instance?.fit(undefined, 20)}>
        <Scan aria-hidden="true" />
      </ToolbarButton>
      <ToolbarButton aria-label="Restablecer" title="Restablecer (0)" onClick={() => instance && resetView(instance)}>
        <RotateCcw aria-hidden="true" />
      </ToolbarButton>
    </Toolbar>
  )
}

const panByKey: Readonly<Partial<Record<string, Position>>> = {
  ArrowLeft: { x: 80, y: 0 },
  ArrowRight: { x: -80, y: 0 },
  ArrowUp: { x: 0, y: 80 },
  ArrowDown: { x: 0, y: -80 },
}

function focusOrder(instance: Core) {
  return [
    instance.nodes('[side = "in"]').map(node => node.id()),
    ["focus"],
    instance.nodes('[side = "out"]').map(node => node.id()),
  ]
}

function drawKeyboardFocus(instance: Core, id: string, reveal = true) {
  const node = instance.$id(id)
  instance.nodes(".kbd-focus").removeClass("kbd-focus")
  node.addClass("kbd-focus")
  if (reveal) {
    const { x1, y1, x2, y2 } = node.renderedBoundingBox()
    if (x1 < 0 || y1 < 0 || x2 > instance.width() || y2 > instance.height()) instance.center(node)
  }
  return node.data("announcement") as string
}

type CanvasProps = FlowProps & { onReady?: (instance: Core | null) => void }

function NodeFlowCanvas({ flow, onOpenNode, onOpenSection, onReady, width, height, nodeWidth, columnGap, mode }: CanvasProps & {
  mode: FlowMode
  height: number
  width: number
  nodeWidth: number
  columnGap: number
}) {
  const canvas = useRef<HTMLDivElement>(null)
  const cy = useRef<Core | null>(null)
  const drawnNodeId = useRef<string | null>(null)
  const actions = useRef({ onOpenNode, onOpenSection })
  const [announcement, setAnnouncement] = useState("")
  const keyboard = useRef<{ columns: string[][]; column: number; row: number }>({ columns: [], column: 1, row: 0 })
  const [density, setDensity] = useState(() => document.documentElement.dataset.density)
  const summary = flowSummary(flow)
  const fullscreen = mode === "fullscreen"

  useLayoutEffect(() => { actions.current = { onOpenNode, onOpenSection } }, [onOpenNode, onOpenSection])

  useLayoutEffect(() => {
    const element = canvas.current!
    const root = document.documentElement
    const restyle = new MutationObserver(() => {
      setDensity(root.dataset.density)
      cy.current?.style(stylesheet(readTokens(element)))
    })
    restyle.observe(root, { attributes: true, attributeFilter: ["class", "style", "data-density"] })
    return () => {
      restyle.disconnect()
      cy.current?.destroy()
      cy.current = null
    }
  }, [])

  useLayoutEffect(() => {
    const element = canvas.current!
    let cancelled = false
    delete element.dataset.ready

    async function draw() {
      // Wait for both weights before Cytoscape measures text for the first time.
      await Promise.allSettled([document.fonts.load('400 13px "Geist"'), document.fonts.load('600 13px "Geist"')])
      if (cancelled) return

      const resetCamera = !fullscreen || !cy.current || drawnNodeId.current !== flow.focus.id
      if (!cy.current) {
        const instance = cytoscape({
          container: element,
          style: stylesheet(readTokens(element)),
          layout: { name: "preset", fit: false },
          minZoom: fullscreen ? 0.5 : 1,
          maxZoom: fullscreen ? 3 : 1,
          userZoomingEnabled: fullscreen,
          userPanningEnabled: fullscreen,
          boxSelectionEnabled: false,
          autoungrabify: true,
          autounselectify: true,
        })
        instance.on("tap", "node[target]", event => actions.current.onOpenNode(event.target.data("target")))
        instance.on("tap", "node.bundle", event => actions.current.onOpenSection(event.target.data("side")))
        instance.on("mouseover", "node[target], node.bundle", () => { element.style.cursor = "pointer" })
        instance.on("mouseout", "node", () => { element.style.cursor = "" })
        cy.current = instance
      }
      const instance = cy.current
      layoutFlow(instance, element, flow, nodeWidth, columnGap, mode)
      if (resetCamera) resetView(instance)
      drawnNodeId.current = flow.focus.id
      if (fullscreen) {
        if (resetCamera) keyboard.current = { columns: focusOrder(instance), column: 1, row: 0 }
        if (document.activeElement === element) {
          const { columns, column, row } = keyboard.current
          // A passive redraw restores the ring without moving the user's viewport.
          setAnnouncement(drawKeyboardFocus(instance, columns[column][row], false))
        }
      }
      element.dataset.ready = "true"
      onReady?.(instance)
    }
    void draw()
    return () => {
      cancelled = true
      delete element.dataset.ready
      onReady?.(null)
    }
  }, [flow, width, height, nodeWidth, columnGap, density, fullscreen, mode, onReady])

  // The renderer's scroll listener is queued; the first press must use the current hit area.
  function refreshPointerBounds() {
    cy.current?.resize()
  }

  function handleKeys(event: KeyboardEvent<HTMLDivElement>) {
    const instance = cy.current
    if (!instance || event.currentTarget.dataset.ready !== "true" || event.altKey || event.ctrlKey || event.metaKey) return
    const pan = event.shiftKey && panByKey[event.key]
    if (pan) instance.panBy(pan)
    else if (event.key === "+" || event.key === "=") zoomBy(instance, zoomInFactor)
    else if (event.key === "-") zoomBy(instance, zoomOutFactor)
    else if (event.key === "0") resetView(instance)
    else if (!event.shiftKey && event.key === "Enter") {
      const { columns, column, row } = keyboard.current
      const node = instance.$id(columns[column][row])
      if (node.hasClass("bundle")) actions.current.onOpenSection(node.data("side"))
      else if (node.data("target")) actions.current.onOpenNode(node.data("target"))
    } else if (!event.shiftKey && panByKey[event.key]) {
      const position = keyboard.current
      const { columns, column, row } = position
      const nextColumn = column + (event.key === "ArrowLeft" ? -1 : event.key === "ArrowRight" ? 1 : 0)
      const rows = columns[nextColumn]
      if (rows?.length) {
        const delta = event.key === "ArrowUp" ? -1 : event.key === "ArrowDown" ? 1 : 0
        const nextRow = Math.max(0, Math.min(rows.length - 1, row + delta))
        if (nextColumn !== column || nextRow !== row) {
          position.column = nextColumn
          position.row = nextRow
          setAnnouncement(drawKeyboardFocus(instance, rows[nextRow]))
        }
      }
    } else return
    event.preventDefault()
  }

  function enterCanvas() {
    const instance = cy.current
    if (!instance || canvas.current?.dataset.ready !== "true") return
    keyboard.current.column = 1
    keyboard.current.row = 0
    setAnnouncement(drawKeyboardFocus(instance, "focus"))
  }

  function leaveCanvas() {
    cy.current?.nodes(".kbd-focus").removeClass("kbd-focus")
    setAnnouncement("")
  }

  const surface = <div ref={canvas} className="node-flow-canvas" role={fullscreen ? "application" : "img"}
    tabIndex={fullscreen ? 0 : undefined} aria-roledescription={fullscreen ? "lienzo" : undefined}
    onKeyDown={fullscreen ? handleKeys : undefined}
    onFocus={fullscreen ? enterCanvas : undefined} onBlur={fullscreen ? leaveCanvas : undefined}
    onPointerDownCapture={refreshPointerBounds}
    aria-label={`Flujo de relaciones de ${flow.focus.title}. ${summary}`} />

  if (fullscreen) return <>{surface}<p className="sr-only" aria-live="polite" aria-atomic="true">{announcement}</p></>

  return (
    <figure className="node-flow">
      {surface}
      <figcaption className="node-flow-caption">
        Haz clic en un nodo para abrirlo o en un grupo para ir a «Llega desde» o «Conduce a». Las listas tienen el detalle completo.
      </figcaption>
    </figure>
  )
}

export function NodeFlow({ mode = "inline", ...props }: CanvasProps & { mode?: FlowMode }) {
  const slot = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })
  const { width, height } = size
  const columns = flowColumns(width) ?? (mode === "fullscreen" && width > 0 ? { nodeWidth: 150, columnGap: 72 } : null)

  useEffect(() => {
    const observer = new ResizeObserver(([{ contentRect }]) => {
      const width = contentRect.width
      const height = mode === "fullscreen" ? contentRect.height : 0
      setSize(current => current.width === width && current.height === height ? current : { width, height })
    })
    observer.observe(slot.current!)
    return () => observer.disconnect()
  }, [mode])

  return (
    <div className="node-flow-slot" ref={slot}>
      {columns && <NodeFlowCanvas {...props} {...columns} width={width} height={height} mode={mode} />}
    </div>
  )
}

export function NodeFlowCard({
  headingRef, getSectionTarget, expandSection, ...props
}: FlowProps & {
  headingRef?: RefObject<HTMLHeadingElement | null>
  getSectionTarget: (side: Side) => HTMLElement | null
  expandSection: (side: Side) => void
}) {
  const [full, setFull] = useState(false)
  const [fullCy, setFullCy] = useState<Core | null>(null)
  const [headingOverflows, setHeadingOverflows] = useState(false)
  const watchHeading = useCallback((element: HTMLDivElement | null) => {
    if (!element) return
    const update = () => setHeadingOverflows(element.scrollHeight > element.clientHeight)
    const observer = new ResizeObserver(update)
    observer.observe(element)
    // The capped box can stay the same size when its text reflows or changes.
    for (const child of element.children) observer.observe(child)
    update()
    return () => observer.disconnect()
  }, [])
  const trigger = useRef<HTMLButtonElement>(null)
  const pendingSection = useRef<Side | null>(null)
  const navigatedWhileOpen = useRef(false)
  const summary = flowSummary(props.flow)

  function clearFocusIntent() {
    pendingSection.current = null
    navigatedWhileOpen.current = false
  }

  function handleOpenChange(next: boolean) {
    if (next) clearFocusIntent()
    setFull(next)
  }

  function openFullNode(id: string) {
    if (id === props.flow.focus.id) return
    navigatedWhileOpen.current = true
    props.onOpenNode(id, { keepFocus: true })
  }

  function openFullSection(side: Side) {
    pendingSection.current = side
    expandSection(side)
    setFull(false)
  }

  function finalFocus() {
    if (pendingSection.current) {
      const target = getSectionTarget(pendingSection.current) ?? trigger.current
      // UI SDK restores with preventScroll, possibly after close completion.
      requestAnimationFrame(() => {
        if (target && document.activeElement === target) target.scrollIntoView({ block: "nearest" })
      })
      return target
    }
    const heading = navigatedWhileOpen.current ? headingRef?.current : null
    if (!heading) return trigger.current
    // UI SDK restores with preventScroll, possibly after close completion.
    requestAnimationFrame(() => {
      if (document.activeElement === heading) heading.scrollIntoView({ block: "center" })
    })
    return heading
  }

  return (
    <Card className="detail-card">
      <CardHeader>
        <CardTitle><h2>Flujo del nodo</h2></CardTitle>
        <CardDescription>{summary}</CardDescription>
        {/* Without an exit animation, UI SDK can complete the close before resolving finalFocus. */}
        <Dialog open={full} onOpenChange={handleOpenChange}>
          <DialogTrigger ref={trigger} data-size="sm" className="node-flow-trigger">
            <Maximize2 aria-hidden="true" /> Pantalla completa
          </DialogTrigger>
          <DialogBackdrop />
          <DialogContent className="node-flow-dialog" finalFocus={finalFocus}>
            <header className="node-flow-dialog-header">
              <div ref={watchHeading} className="node-flow-dialog-heading"
                tabIndex={headingOverflows ? 0 : undefined}
                role={headingOverflows ? "region" : undefined}
                aria-label={headingOverflows ? "Título y resumen del flujo" : undefined}>
                <DialogTitle>Flujo de {props.flow.focus.title}</DialogTitle>
                <DialogDescription>{summary}</DialogDescription>
              </div>
              <FlowZoomToolbar instance={fullCy} />
              <DialogClose data-size="icon" data-variant="ghost" aria-label="Cerrar pantalla completa">
                <X aria-hidden="true" />
              </DialogClose>
            </header>
            <NodeFlow flow={props.flow} mode="fullscreen" onReady={setFullCy}
              onOpenNode={openFullNode} onOpenSection={openFullSection} />
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent><NodeFlow {...props} /></CardContent>
    </Card>
  )
}
