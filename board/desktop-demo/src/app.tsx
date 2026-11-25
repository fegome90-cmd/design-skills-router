import { Toast, ToastRegion, ToastTitle, toast } from "@ui-sdk/react/toast"
import { AgentDrawer } from "@/components/agent-drawer"
import { CommandPalette, type CommandAction } from "@/components/command-palette"
import { LibraryView, ProjectsView, SettingsView } from "@/components/section-views"
import type { OpenNode } from "@/node-flow"
import { ExportGraphButton, isPlainClick, NodeIndex, PluginMapView } from "@/plugin-map"
import { nodeHashPrefix, nodeHref, readNodeId } from "@/graph"
import { Button } from "@ui-sdk/react/button"
import {
  Resizable, ResizableHandle, ResizablePanel, type ResizableLayoutCommitDetails,
} from "@ui-sdk/react/resizable"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@ui-sdk/react/tooltip"
import {
  BookOpen, ChartNoAxesColumnIncreasing, ChevronRight, Circle, File, Folder,
  MessageSquare, Moon, Network, PanelLeftClose, PanelLeftOpen, Route, Settings, Sun, X,
} from "lucide-react"
import { lazy, Suspense, useEffect, useLayoutEffect, useRef, useState, type MouseEvent, type ReactNode } from "react"
import { Badge } from "@/components/ui/badge"
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupLabel,
  SidebarHeader, SidebarInset, SidebarMenu, SidebarMenuButton, SidebarMenuItem,
  SidebarProvider, useSidebar,
} from "@/components/ui/sidebar"
import { ChatView, ConversationList } from "@/chat"
import { demoConversations, documents, projects, type Conversation, type Message, type Period } from "@/data"
import { readPreference, readSidebarWidth, sidebarRange, useDestination, useTheme, writePreference, type Destination } from "@/preferences"

const DashboardView = lazy(() => import("@/dashboard"))

const dashboardAnchors = [
  { id: "resumen", label: "Resumen", icon: ChartNoAxesColumnIncreasing },
  { id: "actividad", label: "Actividad", icon: ChartNoAxesColumnIncreasing },
  { id: "proyectos-recientes", label: "Proyectos recientes", icon: Folder },
]

const appSections = {
  chat: { name: "Chat", contextual: "Conversaciones", icon: MessageSquare },
  dashboard: { name: "Dashboard", contextual: "Analítica", icon: ChartNoAxesColumnIncreasing },
  projects: { name: "Proyectos", contextual: "Proyectos", icon: Folder },
  library: { name: "Biblioteca", contextual: "Biblioteca", icon: BookOpen },
  map: { name: "Mapa del plugin", contextual: "Nodos del plugin", icon: Network },
  settings: { name: "Configuración", contextual: "Configuración", icon: Settings },
} as const satisfies Record<Destination, { name: string; contextual: string; icon: typeof MessageSquare }>

const primarySections = ["chat", "dashboard", "projects", "library", "map"] as const

function Rail({ section }: { section: Destination }) {
  const { isMobile, open, openMobile, toggleSidebar, railToggleRef } = useSidebar()
  const panelOpen = isMobile ? openMobile : open
  const toggleLabel = panelOpen ? "Ocultar panel contextual" : "Mostrar panel contextual"
  const route = (id: Destination) => {
    const { name, icon: Icon } = appSections[id]
    return (
      <SidebarMenuItem key={id}>
        <Tooltip delay={400}>
          <TooltipTrigger
            render={
              <SidebarMenuButton
                className="rail-link bg-transparent"
                render={<a href={`#${id}`} />}
                isActive={id === section}
                aria-current={id === section ? "page" : undefined}
                aria-label={name}
              />
            }
          >
            <Icon aria-hidden="true" />
          </TooltipTrigger>
          <TooltipContent side="right">{name}</TooltipContent>
        </Tooltip>
      </SidebarMenuItem>
    )
  }

  return (
    <Sidebar collapsible="none" className="navigation-rail">
      <SidebarHeader className="rail-brand">
        <div className="brand-mark" role="img" aria-label="Design Skills Router">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
            focusable="false"
          >
            <path
              d="M3.7 7.5C2.1 4.5 5.1 1.5 8.2 3.1
                c1.9 1 2.3 4 4.1 4.9 1.7.8 3.2-1.2 5.3-1.8
                3.2-.9 5.6 2.4 3.9 4.9-1.3 1.9-5 1.3-6.2 3.2
                -1.1 1.8.3 4.3-1 6.2-1.6 2.5-5.7 1.7-6.4-1.4
                -.6-2.5 1.3-4.6.6-6.5-.7-1.8-3.5-2.5-4.8-5.1Z"
            />
          </svg>
        </div>
      </SidebarHeader>
      <SidebarContent className="rail-body">
        <nav className="rail-nav" aria-label="Navegación principal">
          <SidebarMenu className="rail-primary">{primarySections.map(route)}</SidebarMenu>
          <SidebarMenu className="rail-secondary">
            {route("settings")}
            <SidebarMenuItem>
              <Tooltip delay={400}>
                <TooltipTrigger
                  render={
                    <Button
                      ref={railToggleRef}
                      data-variant="ghost"
                      data-size="icon"
                      className="rail-toggle"
                      onClick={toggleSidebar}
                      aria-expanded={panelOpen}
                      aria-controls={panelOpen ? "desktop-context-content" : undefined}
                      aria-haspopup={isMobile ? "dialog" : undefined}
                      aria-label={toggleLabel}
                    />
                  }
                >
                  {panelOpen ? <PanelLeftClose aria-hidden="true" /> : <PanelLeftOpen aria-hidden="true" />}
                </TooltipTrigger>
                <TooltipContent side="right">{toggleLabel}</TooltipContent>
              </Tooltip>
            </SidebarMenuItem>
          </SidebarMenu>
        </nav>
      </SidebarContent>
    </Sidebar>
  )
}

function ResourceList({
  label,
  items,
  selected,
  onSelect,
  icon: Icon,
}: {
  label: string
  items: ReadonlyArray<{ id: string; name: string }>
  selected: string
  onSelect: (id: string) => void
  icon: typeof File
}) {
  return (
    <SidebarGroup className="context-group context-resources">
      <SidebarGroupLabel className="context-label">{label}</SidebarGroupLabel>
      <SidebarMenu className="gap-1">
        {items.map(item => (
          <SidebarMenuItem key={item.id}>
            <SidebarMenuButton
              className="context-row"
              isActive={item.id === selected}
              aria-current={item.id === selected ? "true" : undefined}
              onClick={() => onSelect(item.id)}
            >
              <Icon aria-hidden="true" /><span className="context-row-main">{item.name}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  )
}

function ContextContents({ section, children }: { section: Destination; children: ReactNode }) {
  const { isMobile, setOpenMobile } = useSidebar()
  return (
    <aside className="context-panel" id="desktop-context-content" aria-label="Panel contextual">
      <SidebarHeader className="context-header">
        <div><p>Design Skills Router</p><h2>{appSections[section].contextual}</h2></div>
        {isMobile && (
          <Button
            data-variant="ghost"
            data-size="icon"
            aria-label="Cerrar panel contextual"
            onClick={() => setOpenMobile(false)}
          >
            <X aria-hidden="true" />
          </Button>
        )}
      </SidebarHeader>
      <SidebarContent className="context-body">{children}</SidebarContent>
      <SidebarFooter className="context-footer">
        <span className="workspace-mark" aria-hidden="true"><Route size={15} /></span>
        <div><strong>Pizarra</strong><span>Espacio de demostración</span></div>
      </SidebarFooter>
    </aside>
  )
}

function WorkspaceLayout({
  section,
  theme,
  onTheme,
  context,
  toolbar,
  sidebarWidth,
  onSidebarWidthChange,
  children,
}: {
  section: Destination
  theme: "light" | "dark"
  onTheme: () => void
  context: ReactNode
  toolbar: ReactNode
  sidebarWidth: number
  onSidebarWidthChange: (width: number) => void
  children: ReactNode
}) {
  const { isMobile, open } = useSidebar()
  const panelGroup = useRef<HTMLDivElement>(null)
  const sidebarHandle = useRef<HTMLDivElement>(null)
  const contextualPanel = <ContextContents section={section}>{context}</ContextContents>
  const themeLabel = theme === "light" ? "Activar tema oscuro" : "Activar tema claro"

  function commitSidebarWidth(layout: number[], details: ResizableLayoutCommitDetails) {
    if (details.reason !== "drag" && details.reason !== "step-key" && details.reason !== "imperative") return
    if (!panelGroup.current || layout.length < 2) return
    const handleWidth = sidebarHandle.current?.offsetWidth ?? 0
    const panelSpace = panelGroup.current.clientWidth - handleWidth
    const pixels = Math.round((panelSpace * layout[0]) / 100)
    const width = Math.min(sidebarRange.maximum, Math.max(sidebarRange.minimum, pixels))
    onSidebarWidthChange(width)
  }

  return (
    <>
      <Rail section={section} />
      {isMobile && <Sidebar>{contextualPanel}</Sidebar>}
      <Resizable
        ref={panelGroup}
        className="shell-panels"
        orientation="horizontal"
        onLayoutCommit={commitSidebarWidth}
      >
        {!isMobile && open && (
          <ResizablePanel
            key="context"
            id="resizable-context"
            defaultSize={`${sidebarWidth}px`}
            minSize={`${sidebarRange.minimum}px`}
            maxSize={`${sidebarRange.maximum}px`}
          >
            <Sidebar collapsible="none" className="desktop-context">{contextualPanel}</Sidebar>
          </ResizablePanel>
        )}
        {!isMobile && open && (
          <ResizableHandle
            key="handle"
            ref={sidebarHandle}
            aria-label="Redimensionar panel contextual"
            className="context-separator"
          />
        )}
        <ResizablePanel key="workspace" id="resizable-workspace">
          <SidebarInset className="workspace">
            <header className="workspace-toolbar">
              <div className="workspace-location">
                <span className="location-root">Pizarra</span>
                <ChevronRight aria-hidden="true" className="location-chevron" />
                <strong>{appSections[section].name}</strong>
              </div>
              <div className="toolbar-actions">
                {toolbar}
                <Badge variant="outline" className="demo-badge"><span aria-hidden="true" />Demo local</Badge>
                <Tooltip delay={400}>
                  <TooltipTrigger
                    render={
                      <Button
                        data-size="icon"
                        className="theme-toggle"
                        onClick={onTheme}
                        aria-label={themeLabel}
                      />
                    }
                  >
                    {theme === "light" ? <Moon aria-hidden="true" /> : <Sun aria-hidden="true" />}
                  </TooltipTrigger>
                  <TooltipContent side="bottom">{themeLabel}</TooltipContent>
                </Tooltip>
              </div>
            </header>
            {children}
          </SidebarInset>
        </ResizablePanel>
      </Resizable>
    </>
  )
}

function DesktopApplication({
  theme,
  onTheme,
}: {
  theme: "light" | "dark"
  onTheme: (theme: "light" | "dark") => void
}) {
  const section = useDestination()
  const [commandOpen, setCommandOpen] = useState(false)
  const [agentOpen, setAgentOpen] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(readSidebarWidth)
  const [density, setDensity] = useState<"comfortable" | "compact">(
    () => readPreference("density") === "compact" ? "compact" : "comfortable"
  )
  const [toastsEnabled, setToastsEnabled] = useState(
    () => readPreference("toasts") !== "disabled"
  )

  useEffect(() => {
    document.documentElement.dataset.density = density
  }, [density])

  function updateSidebarWidth(width: number) {
    setSidebarWidth(width)
    writePreference("sidebar-width", String(width))
  }

  const { isMobile, openMobile, setOpenMobile, mobileReturnFocusRef } = useSidebar()
  const [nodeId, setNodeId] = useState(() => readNodeId(window.location.hash))
  const [nodeQuery, setNodeQuery] = useState("")
  const [nodeGroup, setNodeGroup] = useState("")
  const nodeHeading = useRef<HTMLHeadingElement>(null)
  const focusNodeHeading = useRef(false)
  const [threads, setThreads] = useState(demoConversations)
  const [selectedThread, selectThread] = useState(demoConversations[0].id)
  const [search, setSearch] = useState("")
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [period, setPeriod] = useState<Period>(30)
  const [dashboardAnchor, selectDashboardAnchor] = useState(dashboardAnchors[0].id)
  const [project, selectProject] = useState(projects[0].id)
  const [documentId, selectDocument] = useState(documents[0].id)
  const thread = threads.find(item => item.id === selectedThread) ?? threads[0]

  function closeMobilePanel() {
    if (isMobile) setOpenMobile(false)
  }

  useEffect(() => {
    const readNode = () => {
      if (window.location.hash.startsWith(nodeHashPrefix)) setNodeId(readNodeId(window.location.hash))
    }
    window.addEventListener("hashchange", readNode)
    return () => window.removeEventListener("hashchange", readNode)
  }, [])

  useLayoutEffect(() => {
    if (!focusNodeHeading.current) return
    focusNodeHeading.current = false
    nodeHeading.current?.focus()
  }, [nodeId])

  // The link keeps its default navigation, so the hash and the browser history
  // stay the source of truth; this only decides where focus lands afterwards.
  function selectNode(event: MouseEvent<HTMLAnchorElement>, targetId: string) {
    if (!isPlainClick(event)) return
    const changed = targetId !== nodeId
    if (isMobile && openMobile && section === "map") {
      if (changed) mobileReturnFocusRef.current = nodeHeading.current
      setOpenMobile(false)
    } else {
      focusNodeHeading.current = changed
    }
  }

  // Opening a node from the flow canvas goes through the hash, like a link.
  const openNode: OpenNode = (targetId, { keepFocus = false } = {}) => {
    focusNodeHeading.current = !keepFocus && targetId !== nodeId
    window.location.hash = nodeHref(targetId)
  }

  function createThread() {
    const next: Conversation = {
      id: crypto.randomUUID(),
      origin: "local",
      title: "Nueva conversación",
      date: "Ahora",
      messages: [],
    }
    setThreads(items => [next, ...items])
    selectThread(next.id)
    setSearch("")
    closeMobilePanel()
  }

  function setDraft(value: string) {
    setDrafts(values => ({ ...values, [thread.id]: value }))
  }

  function sendMessage(text: string) {
    const message: Message = { id: crypto.randomUUID(), role: "user", paragraphs: [text] }
    const nextTitle = text.length > 42 ? `${text.slice(0, 42)}…` : text
    setThreads(items => items.map(item =>
      item.id === thread.id
        ? { ...item, title: item.messages.length ? item.title : nextTitle, messages: [...item.messages, message] }
        : item
    ))
    setDraft("")
  }

  const contexts = {
    chat: <ConversationList conversations={threads} selected={thread.id} query={search} onSearch={setSearch} onSelect={id => { selectThread(id); closeMobilePanel() }} onCreate={createThread} />,
    dashboard: (
      <SidebarGroup className="context-group context-resources">
        <SidebarGroupLabel className="context-label">Panel de actividad</SidebarGroupLabel>
        <SidebarMenu className="gap-1">
          {dashboardAnchors.map(({ id, label, icon: Icon }) => (
            <SidebarMenuItem key={id}>
              <SidebarMenuButton
                className="context-row"
                isActive={id === dashboardAnchor}
                aria-current={id === dashboardAnchor ? "true" : undefined}
                onClick={() => {
                  selectDashboardAnchor(id)
                  closeMobilePanel()
                  document.getElementById(id)?.scrollIntoView({ block: "start" })
                }}
              >
                <Icon aria-hidden="true" /><span>{label}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroup>
    ),
    projects: <ResourceList label="Proyectos del espacio" items={projects} selected={project} icon={Folder} onSelect={id => { selectProject(id); closeMobilePanel() }} />,
    library: <ResourceList label="Documentos" items={documents} selected={documentId} icon={File} onSelect={id => { selectDocument(id); closeMobilePanel() }} />,
    map: <NodeIndex selected={nodeId} query={nodeQuery} onQuery={setNodeQuery} group={nodeGroup} onGroup={setNodeGroup} onSelect={selectNode} />,
    settings: <ResourceList label="Preferencias" items={[{ id: "apariencia", name: "Apariencia" }]} selected="apariencia" icon={Circle} onSelect={id => {
      closeMobilePanel()
      document.getElementById(id)?.scrollIntoView({ block: "start" })
    }} />,
  }

  function notify(message: string, ok = true) {
    if (toastsEnabled) toast(message, { type: ok ? "success" : "error" })
  }

  const views = {
    chat: <ChatView conversation={thread} draft={drafts[thread.id] ?? ""} onDraft={setDraft} onSend={sendMessage} />,
    dashboard: <DashboardView period={period} onPeriod={setPeriod} onProject={id => { selectProject(id); window.location.hash = "projects" }} />,
    projects: <ProjectsView projectId={project} onSelectProject={selectProject} onNotify={notify} />,
    library: <LibraryView documentId={documentId} onSelectDocument={selectDocument} />,
    map: <PluginMapView nodeId={nodeId} headingRef={nodeHeading} onSelect={selectNode} onOpenNode={openNode} />,
    settings: <SettingsView
      theme={theme}
      onThemeChange={onTheme}
      density={density}
      onDensityChange={value => {
        setDensity(value)
        writePreference("density", value)
      }}
      sidebarWidth={sidebarWidth}
      onSidebarWidthChange={updateSidebarWidth}
      toastsEnabled={toastsEnabled}
      onToastsChange={value => {
        setToastsEnabled(value)
        writePreference("toasts", value ? "enabled" : "disabled")
      }}
    />,
  }

  const commands: CommandAction[] = Object.entries(appSections).map(([id, entry]) => ({
    id,
    label: entry.name,
    icon: entry.icon,
    group: "Navegación",
    onSelect: () => { window.location.hash = id },
  }))

  return (
    <WorkspaceLayout
      section={section}
      theme={theme}
      onTheme={() => onTheme(theme === "light" ? "dark" : "light")}
      context={contexts[section]}
      sidebarWidth={sidebarWidth}
      onSidebarWidthChange={updateSidebarWidth}
      toolbar={<>
        {section === "map" && <ExportGraphButton />}
        <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} actions={commands} />
        <AgentDrawer open={agentOpen} onOpenChange={setAgentOpen} onRunMacroResult={notify} />
      </>}
    >
      {section === "chat"
        ? views.chat
        : <div className="workspace-scroll" key={section}><Suspense fallback={<p className="view-loading" role="status">Cargando el dashboard…</p>}>{views[section]}</Suspense></div>}
      <ToastRegion>{() => <Toast><ToastTitle /></Toast>}</ToastRegion>
    </WorkspaceLayout>
  )
}

export function App() {
  const [open, setOpen] = useState(() => readPreference("sidebar") !== "closed")
  const [theme, setTheme] = useTheme()
  return (
    <SidebarProvider className="app-shell" open={open} onOpenChange={value => {
      setOpen(value)
      writePreference("sidebar", value ? "open" : "closed")
    }}>
      <DesktopApplication theme={theme} onTheme={setTheme} />
    </SidebarProvider>
  )
}
