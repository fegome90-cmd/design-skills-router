import type {
  AgentComponent,
  AgentStep,
  ObservedChange,
} from "@ui-sdk/react/agent"
import {
  AlertDialog,
  AlertDialogBackdrop,
  AlertDialogClose,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
} from "@ui-sdk/react/alert-dialog"
import {
  Drawer,
  DrawerBackdrop,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerTitle,
} from "@ui-sdk/react/drawer"
import { Tabs, TabsList, TabsPanel, TabsTab } from "@ui-sdk/react/tabs"
import { Bot, Play, RefreshCw, ShieldAlert, Trash2, X } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import type * as React from "react"
import { agent } from "@/agent"
import { Button } from "@ui-sdk/react/button"
import { Input } from "@ui-sdk/react/input"

type AgentActResult = Awaited<ReturnType<typeof agent.act>>

type LoggedEvent = {
  id: string
  time: string
  change: ObservedChange
}

function formatStateSummary(entry: AgentComponent) {
  const details: string[] = []
  if ("value" in entry && entry.value !== undefined) {
    details.push(`value: ${JSON.stringify(entry.value)}`)
  }
  if ("pressed" in entry && entry.pressed !== undefined) {
    details.push(`pressed: ${String(entry.pressed)}`)
  }
  if ("open" in entry && entry.open !== undefined) {
    details.push(`open: ${String(entry.open)}`)
  }
  return details
}

export function AgentConfirmDialog({
  request,
  onResolve,
}: {
  request: { message: string } | null
  onResolve: (approved: boolean) => void
}) {
  return (
    <AlertDialog
      open={Boolean(request)}
      onOpenChange={(nextOpen, details) => {
        if (!nextOpen) {
          onResolve(details.returnValue === "confirm")
        }
      }}
    >
      <AlertDialogBackdrop />
      <AlertDialogContent
        className="agent-confirm-dialog"
        data-agent-hidden=""
      >
        <div className="agent-confirm-header">
          <ShieldAlert aria-hidden="true" className="size-4 text-destructive" />
          <AlertDialogTitle>Confirmar acción del agente</AlertDialogTitle>
        </div>
        <AlertDialogDescription>
          {request?.message ?? "Esta acción protegida requiere tu autorización."}
        </AlertDialogDescription>
        <div className="agent-confirm-actions">
          <AlertDialogClose
            value="deny"
            data-size="sm"
          >
            Denegar
          </AlertDialogClose>
          <AlertDialogClose
            value="confirm"
            data-variant="destructive"
            data-size="sm"
          >
            Autorizar
          </AlertDialogClose>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  )
}

export function AgentDrawer({
  open,
  onOpenChange,
  onRunMacroResult,
  triggerRef,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onRunMacroResult?: (summary: string, ok: boolean) => void
  triggerRef?: React.RefObject<HTMLButtonElement | null>
}) {
  const [snapshot, setSnapshot] = useState<AgentComponent[]>([])
  const [filter, setFilter] = useState("")
  const [events, setEvents] = useState<LoggedEvent[]>([])
  const [runningMacro, setRunningMacro] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<{
    name: string
    result: AgentActResult
  } | null>(null)

  const refreshSnapshot = useCallback(() => {
    const items = agent
      .snapshot()
      .filter((entry) => !entry.offPage && entry.component !== "more")
    setSnapshot(items)
  }, [])

  useEffect(() => {
    const frame = requestAnimationFrame(() => refreshSnapshot())
    const unsubscribe = agent.subscribe((change) => {
      setEvents((prev) =>
        [
          {
            id: crypto.randomUUID(),
            time: new Date().toLocaleTimeString("es", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            }),
            change,
          },
          ...prev,
        ].slice(0, 25)
      )
      requestAnimationFrame(() => refreshSnapshot())
    })
    return () => {
      cancelAnimationFrame(frame)
      unsubscribe()
    }
  }, [refreshSnapshot])

  useEffect(() => {
    if (!open) return
    const frame = requestAnimationFrame(() => refreshSnapshot())
    return () => cancelAnimationFrame(frame)
  }, [open, refreshSnapshot])

  async function executeMacro(name: string, buildSteps: () => AgentStep[]) {
    setRunningMacro(name)
    try {
      const steps = buildSteps()
      const result = await agent.act({ steps })
      setLastResult({ name, result })
      refreshSnapshot()
      const summary = result.ok
        ? `Flujo «${name}» completado (${result.steps.length} pasos)`
        : `Flujo «${name}» detenido: ${result.error?.message ?? "error"}`
      onRunMacroResult?.(summary, result.ok)
    } finally {
      setRunningMacro(null)
    }
  }

  const normalizedFilter = filter.trim().toLocaleLowerCase("es")
  const filteredSnapshot = normalizedFilter
    ? snapshot.filter((entry) =>
        [entry.ref, entry.component, entry.label, entry.row]
          .filter(Boolean)
          .some((field) =>
            String(field).toLocaleLowerCase("es").includes(normalizedFilter)
          )
      )
    : snapshot

  const count = snapshot.length

  return (
    <>
      <Button
        ref={triggerRef}
        data-size="sm"
        className="agent-trigger"
        aria-label="Agente UI"
        title="Inspector de Agente UI y WebMCP"
        onClick={() => onOpenChange(true)}
      >
        <Bot aria-hidden="true" />
        <span className="toolbar-btn-label">Agente UI</span>
        <span className="agent-count" aria-hidden="true">
          {count}
        </span>
      </Button>

      {/* Non-inert modal keeps background interactive so agent.snapshot/act inspect live app controls. */}
      <Drawer
        side="right"
        open={open}
        onOpenChange={onOpenChange}
        modal="trap-focus"
        closeOnOutsidePress={true}
      >
        <DrawerBackdrop />
        <DrawerContent
          className="agent-drawer"
          finalFocus={triggerRef ? () => triggerRef.current : undefined}
          data-agent-hidden=""
        >
          <div className="agent-drawer-header">
            <div className="agent-drawer-heading">
              <DrawerTitle>Agente UI · WebMCP</DrawerTitle>
              <DrawerDescription>
                Inspección en vivo y ejecución con @ui-sdk/react/agent.
              </DrawerDescription>
            </div>
            <DrawerClose
              data-variant="ghost"
              data-size="icon-sm"
              aria-label="Cerrar inspector del agente"
            >
              <X aria-hidden="true" />
            </DrawerClose>
          </div>

          <Tabs defaultValue="macros" className="agent-drawer-tabs">
            <TabsList
              aria-label="Modos del inspector"
              className="agent-drawer-tablist"
            >
              <TabsTab value="macros">Flujos</TabsTab>
              <TabsTab value="snapshot">Snapshot</TabsTab>
              <TabsTab value="events">Eventos</TabsTab>
            </TabsList>

            <TabsPanel value="macros" className="agent-drawer-panel">
              <div className="agent-macro-list">
                <Button
                  data-size="sm"
                  className="agent-macro-btn"
                  disabled={runningMacro !== null}
                  onClick={() =>
                    void executeMacro("Crear hilo y enviar nota", () => {
                      const current = agent.snapshot()
                      const hasNewThread = current.some(
                        (entry) =>
                          !entry.offPage &&
                          entry.label === "Nueva conversación"
                      )
                      const chatNav = current.find(
                        (entry) =>
                          !entry.offPage &&
                          entry.label === "Chat" &&
                          entry.actions.includes("press")
                      )
                      const steps: AgentStep[] = [
                        { ref: "Nueva conversación", action: "press" },
                        {
                          ref: "Escribe un mensaje",
                          action: "setValue",
                          args: ["Nota creada por @ui-sdk/react/agent"],
                        },
                        { ref: "Enviar mensaje", action: "press" },
                      ]
                      return !hasNewThread && chatNav
                        ? [{ ref: chatNav.ref, action: "press" }, ...steps]
                        : steps
                    })
                  }
                >
                  <Play aria-hidden="true" />
                  Crear hilo y enviar nota
                </Button>

                <Button
                  data-size="sm"
                  className="agent-macro-btn"
                  disabled={runningMacro !== null}
                  onClick={() =>
                    void executeMacro("Ir a Dashboard (7 días)", () => [
                      { ref: "Dashboard", action: "press" },
                      { ref: "7 días", action: "setPressed", args: [true] },
                    ])
                  }
                >
                  <Play aria-hidden="true" />
                  Ir a Dashboard (7 días)
                </Button>

                <Button
                  data-size="sm"
                  className="agent-macro-btn"
                  disabled={runningMacro !== null}
                  onClick={() =>
                    void executeMacro("Buscar un nodo en el mapa", () => {
                      const mapNav = agent
                        .snapshot()
                        .find(
                          (entry) =>
                            !entry.offPage &&
                            entry.label === "Mapa del plugin" &&
                            entry.actions.includes("press")
                        )
                      // Node rows are plain links, so the agent narrows the
                      // index until the node is in view instead of opening it.
                      return [
                        { ref: mapNav?.ref ?? "Mapa del plugin", action: "press" },
                        {
                          ref: "Buscar nodos",
                          action: "setValue",
                          args: ["Router.packet"],
                        },
                        {
                          ref: "Grupo",
                          action: "setValue",
                          args: ["Código del flujo"],
                        },
                      ]
                    })
                  }
                >
                  <Play aria-hidden="true" />
                  Buscar un nodo en el mapa
                </Button>

                <Button
                  data-size="sm"
                  className="agent-macro-btn"
                  disabled={runningMacro !== null}
                  onClick={() =>
                    void executeMacro("Alternar tema", () => {
                      const themeToggle = agent
                        .snapshot()
                        .find(
                          (entry) =>
                            !entry.offPage &&
                            (entry.label === "Activar tema oscuro" ||
                              entry.label === "Activar tema claro")
                        )
                      return [
                        {
                          ref: themeToggle?.ref ?? "Activar tema oscuro",
                          action: "press",
                        },
                      ]
                    })
                  }
                >
                  <Play aria-hidden="true" />
                  Alternar tema
                </Button>

                <Button
                  data-size="sm"
                  className="agent-macro-btn"
                  disabled={runningMacro !== null}
                  onClick={() =>
                    void executeMacro("Probar confirmación protegida", () => {
                      const projectsNav = agent
                        .snapshot()
                        .find(
                          (entry) =>
                            !entry.offPage &&
                            entry.label === "Proyectos" &&
                            entry.actions.includes("press")
                        )
                      return [
                        {
                          ref: projectsNav?.ref ?? "Proyectos",
                          action: "press",
                        },
                        { ref: "Simulador", action: "press" },
                        { ref: "Restablecer avance", action: "press" },
                        { ref: "Restablecer", action: "press" },
                      ]
                    })
                  }
                >
                  <ShieldAlert aria-hidden="true" />
                  Probar confirmación protegida
                </Button>
              </div>

              {lastResult && (
                <div
                  className="agent-result-card"
                  data-ok={lastResult.result.ok ? "true" : "false"}
                >
                  <div className="agent-result-header">
                    <strong>{lastResult.name}</strong>
                    <span className="agent-result-status">
                      {lastResult.result.ok ? "OK" : "Error"}
                    </span>
                  </div>
                  {lastResult.result.error && (
                    <p className="agent-result-error">
                      Paso {lastResult.result.error.step + 1}:{" "}
                      {lastResult.result.error.message}
                    </p>
                  )}
                  <ol className="agent-result-steps">
                    {lastResult.result.steps.map((step) => (
                      <li key={`${step.step}-${step.ref}`}>
                        <code>{step.ref}</code>
                        {step.result !== undefined && (
                          <span> · {String(step.result)}</span>
                        )}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </TabsPanel>

            <TabsPanel value="snapshot" className="agent-drawer-panel">
              <div className="agent-snapshot-tools">
                <Input
                  value={filter}
                  onValueChange={setFilter}
                  aria-label="Filtrar snapshot"
                  placeholder="Filtrar por ref, componente o etiqueta…"
                />
                <Button
                  data-size="sm"
                  onClick={refreshSnapshot}
                >
                  <RefreshCw aria-hidden="true" />
                  Actualizar
                </Button>
              </div>
              <div className="agent-snapshot-list">
                {filteredSnapshot.map((entry) => {
                  const stateSummary = formatStateSummary(entry)
                  return (
                    <div key={entry.ref} className="agent-snapshot-item">
                      <div className="agent-snapshot-meta">
                        <code className="agent-ref">{entry.ref}</code>
                        <span className="agent-kind">{entry.component}</span>
                        {entry.confirm && (
                          <span className="agent-confirm-tag">confirm</span>
                        )}
                      </div>
                      <p className="agent-snapshot-label">
                        {entry.label ?? entry.row ?? "Sin etiqueta"}
                      </p>
                      <p className="agent-snapshot-actions">
                        {entry.actions.length > 0
                          ? entry.actions.join(", ")
                          : "solo lectura"}
                      </p>
                      {stateSummary.length > 0 && (
                        <p className="agent-snapshot-state">
                          {stateSummary.join(" · ")}
                        </p>
                      )}
                    </div>
                  )
                })}
                {filteredSnapshot.length === 0 && (
                  <p className="agent-empty-state">
                    No hay componentes visibles que coincidan.
                  </p>
                )}
              </div>
            </TabsPanel>

            <TabsPanel value="events" className="agent-drawer-panel">
              <div className="agent-events-tools">
                <span className="agent-events-count">
                  {events.length} recientes
                </span>
                <Button
                  data-size="sm"
                  onClick={() => setEvents([])}
                >
                  <Trash2 aria-hidden="true" />
                  Limpiar eventos
                </Button>
              </div>
              <div className="agent-events-list">
                {events.map(({ id, time, change }) => (
                  <div key={id} className="agent-event-item">
                    <div className="agent-event-meta">
                      <code>{change.ref}</code>
                      <span>{change.component}</span>
                      <span>{time}</span>
                    </div>
                    <p className="agent-event-label">
                      {change.label ?? change.key}:{" "}
                      <code>{JSON.stringify(change.previous)}</code> →{" "}
                      <code>{JSON.stringify(change.value)}</code>
                    </p>
                    <p className="agent-event-source">
                      {change.source} · {change.reason}
                    </p>
                  </div>
                ))}
                {events.length === 0 && (
                  <p className="agent-empty-state">
                    Interactúa con la app o ejecuta un flujo para ver eventos.
                  </p>
                )}
              </div>
            </TabsPanel>
          </Tabs>
        </DrawerContent>
      </Drawer>
    </>
  )
}
