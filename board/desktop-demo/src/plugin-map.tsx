import { Button } from "@ui-sdk/react/button"
import { Collapsible, CollapsiblePanel, CollapsibleTrigger } from "@ui-sdk/react/collapsible"
import { Field, FieldLabel } from "@ui-sdk/react/field"
import { Input, InputClear, InputGroup } from "@ui-sdk/react/input"
import {
  Select, SelectContent, SelectItem, SelectItemIndicator, SelectTrigger, SelectValue,
} from "@ui-sdk/react/select"
import { Check, ChevronDown, Download, FileCode, X } from "lucide-react"
import { useMemo, useRef, useState, type MouseEvent, type Ref, type RefObject } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { SidebarGroup, SidebarGroupLabel, SidebarMenu, SidebarMenuButton, SidebarMenuItem } from "@/components/ui/sidebar"
import { NodeFlowCard, type OpenNode } from "@/node-flow"
import { directedRelations, exportGraph, findNodes, flowProjection, nodeGroups, nodeHref, nodes, type GraphNode, type Relation } from "@/graph"

const allGroups = "__all__"
const groupOptions = [
  { value: allGroups, label: "Todos los grupos" },
  ...nodeGroups.map(group => ({ value: group, label: group })),
]

export function isPlainClick(event: MouseEvent) {
  return !event.defaultPrevented && event.button === 0 &&
    !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey
}

export function NodeIndex({
  selected,
  query,
  onQuery,
  group,
  onGroup,
  onSelect,
}: {
  selected: string
  query: string
  onQuery: (query: string) => void
  group: string
  onGroup: (group: string) => void
  onSelect: (event: MouseEvent<HTMLAnchorElement>, id: string) => void
}) {
  const matches = findNodes(query, group)

  return (
    <nav aria-label="Nodos del plugin" className="node-index">
      <div className="context-tools">
        <InputGroup className="context-search-group h-9 rounded-lg border-input bg-card">
          <Input
            className="context-search"
            type="search"
            aria-label="Buscar nodos"
            placeholder="Archivo, ID o símbolo"
            value={query}
            onValueChange={onQuery}
          />
          {query && (
            <InputClear aria-label="Limpiar búsqueda">
              <X aria-hidden="true" />
            </InputClear>
          )}
        </InputGroup>
        <Field>
          <FieldLabel className="sr-only">Grupo</FieldLabel>
          <Select
            value={group || allGroups}
            items={groupOptions}
            onValueChange={value => onGroup(!value || value === allGroups ? "" : String(value))}
          >
            <SelectTrigger className="node-group-filter" aria-label="Grupo">
              <SelectValue placeholder="Todos los grupos" />
              <ChevronDown aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
            </SelectTrigger>
            <SelectContent>
              {groupOptions.map(option => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                  <SelectItemIndicator><Check className="size-4" aria-hidden="true" /></SelectItemIndicator>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      </div>
      <SidebarGroup className="context-group">
        <SidebarGroupLabel className="context-label">
          <span role="status">{matches.length} {matches.length === 1 ? "nodo" : "nodos"}</span>
        </SidebarGroupLabel>
        {matches.length === 0 ? <p className="context-empty">Ningún nodo coincide con la búsqueda.</p> : (
          <SidebarMenu className="gap-1">
            {matches.map(node => (
              <SidebarMenuItem key={node.id}>
                <SidebarMenuButton
                  className="context-row node-row"
                  isActive={node.id === selected}
                  aria-current={node.id === selected ? "location" : undefined}
                  render={<a href={nodeHref(node.id)} onClick={event => onSelect(event, node.id)} />}
                >
                  <span className="node-row-text">
                    <span className="context-row-main">{node.title}</span>
                    <span className="context-meta">{node.id} · {node.group}</span>
                  </span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        )}
      </SidebarGroup>
    </nav>
  )
}

function NodeFacts({ node }: { node: GraphNode }) {
  return (
    <dl className="node-facts">
      <dt>Identificador</dt>
      <dd><code>{node.id}</code></dd>
      <dt>Archivo</dt>
      <dd><code>{node.path}</code></dd>
      {node.symbol && <><dt>Símbolo</dt><dd><code>{node.symbol}</code></dd></>}
      {Number.isInteger(node.line) && <><dt>Línea</dt><dd>{node.line}</dd></>}
    </dl>
  )
}

export function ExportGraphButton() {
  return (
    <Button
      data-size="sm"
      className="command-trigger"
      onClick={exportGraph}
      aria-label="Exportar mapa"
      title="Exportar el mapa en JSON"
    >
      <Download aria-hidden="true" />
      <span className="toolbar-btn-label">Exportar JSON</span>
    </Button>
  )
}

const relationFoldLimit = 14

export type RelationSide = "in" | "out"
type RelationSectionId = RelationSide | "python-in" | "python-out"

function RelationRows({ title, relations, listRef, onSelect }: {
  title: string
  relations: Relation[]
  listRef?: Ref<HTMLUListElement>
  onSelect: (event: MouseEvent<HTMLAnchorElement>, id: string) => void
}) {
  return (
    <ul className="node-relations" aria-label={title} ref={listRef} tabIndex={listRef ? -1 : undefined}>
      {relations.map(({ edge, other }) => (
        <li key={JSON.stringify([edge.from, edge.to, edge.kind, edge.condition])}>
          <a href={nodeHref(other.id)} onClick={event => onSelect(event, other.id)}>
            {other.title || other.id}
            {other.title && other.title !== other.id ? ` · ${other.id}` : ""}
          </a>
          {edge.condition && <p>{edge.condition}</p>}
        </li>
      ))}
    </ul>
  )
}

export function RelationSection({ title, relations, open, onOpenChange, triggerRef, listRef, onSelect }: {
  title: string
  relations: Relation[]
  open: boolean
  onOpenChange: (open: boolean) => void
  triggerRef?: Ref<HTMLButtonElement>
  listRef?: Ref<HTMLUListElement>
  onSelect: (event: MouseEvent<HTMLAnchorElement>, id: string) => void
}) {
  if (relations.length === 0) return null
  const rows = <RelationRows title={title} relations={relations}
    listRef={relations.length <= relationFoldLimit ? listRef : undefined} onSelect={onSelect} />
  return (
    <section className="relation-section">
      {relations.length <= relationFoldLimit ? <><h3>{title}</h3>{rows}</> : (
        <Collapsible open={open} onOpenChange={onOpenChange}>
          <h3>
            <CollapsibleTrigger ref={triggerRef} className="relation-fold-trigger">
              {title} · {relations.length}
              <ChevronDown aria-hidden="true" className="size-4 node-source-chevron" />
            </CollapsibleTrigger>
          </h3>
          <CollapsiblePanel>{rows}</CollapsiblePanel>
        </Collapsible>
      )}
    </section>
  )
}

export function PluginMapView({
  nodeId,
  headingRef,
  onSelect,
  onOpenNode,
}: {
  nodeId: string
  headingRef: RefObject<HTMLHeadingElement | null>
  onSelect: (event: MouseEvent<HTMLAnchorElement>, id: string) => void
  onOpenNode: OpenNode
}) {
  const node = nodes.get(nodeId)!
  const relations = directedRelations(nodeId)
  const flow = useMemo(() => flowProjection(nodeId), [nodeId])
  const [folds, setFolds] = useState<{ nodeId: string; open: Partial<Record<RelationSectionId, boolean>> }>({ nodeId, open: {} })
  const incomingTriggerRef = useRef<HTMLButtonElement>(null)
  const outgoingTriggerRef = useRef<HTMLButtonElement>(null)
  const incomingListRef = useRef<HTMLUListElement>(null)
  const outgoingListRef = useRef<HTMLUListElement>(null)
  // Drop the previous node's folds, including when Back restores its hash.
  if (folds.nodeId !== nodeId) setFolds({ nodeId, open: {} })

  function setSide(side: RelationSectionId, open: boolean) {
    setFolds(current => ({ nodeId, open: { ...current.open, [side]: open } }))
  }

  function sectionTrigger(side: RelationSide) {
    return (side === "in" ? incomingTriggerRef : outgoingTriggerRef).current
  }

  function sectionTarget(side: RelationSide) {
    return sectionTrigger(side) ?? (side === "in" ? incomingListRef : outgoingListRef).current
  }

  function expandSection(side: RelationSide) {
    if (sectionTrigger(side)) setSide(side, true)
  }

  function openSection(side: RelationSide) {
    expandSection(side)
    const destination = sectionTarget(side)
    destination?.focus({ preventScroll: true })
    destination?.scrollIntoView({ block: "start" })
  }

  const outgoing = relations.outgoing.length + relations.pythonOutgoing.length
  const incoming = relations.incoming.length + relations.pythonIncoming.length
  const total = outgoing + incoming
  const sections = [
    { id: "python-out", title: "Accede a código Python", relations: relations.pythonOutgoing, triggerRef: undefined, listRef: undefined },
    { id: "python-in", title: "Consultado desde código Python", relations: relations.pythonIncoming, triggerRef: undefined, listRef: undefined },
    { id: "out", title: "Conduce a", relations: relations.outgoing, triggerRef: outgoingTriggerRef, listRef: outgoingListRef },
    { id: "in", title: "Llega desde", relations: relations.incoming, triggerRef: incomingTriggerRef, listRef: incomingListRef },
  ] as const

  return (
    <article className="standard-view plugin-map">
      <header className="page-heading">
        <div>
          <p className="eyebrow">{node.group}</p>
          <h1 ref={headingRef} id={`router-node-${node.id}`} tabIndex={-1}>{node.title}</h1>
          {node.summary && <p>{node.summary}</p>}
        </div>
      </header>

      <Card className="detail-card">
        <CardHeader>
          <CardTitle><h2>Ubicación en el código</h2></CardTitle>
        </CardHeader>
        <CardContent>
          <NodeFacts node={node} />
          {node.source && (
            <Collapsible key={node.id} className="node-source">
              <CollapsibleTrigger>
                <FileCode aria-hidden="true" className="size-4" />
                Ver fuente
                <ChevronDown aria-hidden="true" className="size-4 node-source-chevron" />
              </CollapsibleTrigger>
              <CollapsiblePanel><pre>{node.source}</pre></CollapsiblePanel>
            </Collapsible>
          )}
        </CardContent>
      </Card>

      <Card className="detail-card">
        <CardHeader>
          <CardTitle><h2>Relaciones</h2></CardTitle>
          <CardDescription>
            {total === 0 ? "Sin relaciones registradas." : `${outgoing} salientes y ${incoming} entrantes.`}
          </CardDescription>
        </CardHeader>
        {total > 0 && (
          <CardContent className="relation-sections">
            {sections.map(({ id, title, relations: rows, triggerRef, listRef }) => (
              <RelationSection
                key={id}
                title={title}
                relations={rows}
                open={folds.open[id] ?? false}
                onOpenChange={open => setSide(id, open)}
                onSelect={onSelect}
                triggerRef={triggerRef}
                listRef={listRef}
              />
            ))}
          </CardContent>
        )}
      </Card>

      <NodeFlowCard flow={flow} onOpenNode={onOpenNode} onOpenSection={openSection}
        headingRef={headingRef} getSectionTarget={sectionTarget} expandSection={expandSection} />
    </article>
  )
}
