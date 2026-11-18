import {
  BookOpen, ChartNoAxesColumnIncreasing, ChevronRight, Circle, FileText, Folder,
  FolderKanban, MessageSquare, Moon, PanelLeftClose, PanelLeftOpen, Route, Settings, Sun, X,
} from "lucide-react"
import { lazy, Suspense, useRef, useState, type ReactNode } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupLabel,
  SidebarHeader, SidebarInset, SidebarMenu, SidebarMenuButton, SidebarMenuItem,
  SidebarProvider, useSidebar,
} from "@/components/ui/sidebar"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { ChatView, ConversationList } from "@/chat"
import { ProjectStatus } from "@/components/project-status"
import { demoConversations, documents, projects, type Conversation, type Message, type Period } from "@/data"
import { readPreference, readSidebarWidth, sidebarRange, useDestination, useTheme, writePreference, type Destination } from "@/preferences"

const DashboardView = lazy(() => import("@/dashboard"))

const dashboardAnchors = [
  { id: "resumen", label: "Resumen", icon: ChartNoAxesColumnIncreasing },
  { id: "actividad", label: "Actividad", icon: ChartNoAxesColumnIncreasing },
  { id: "proyectos-recientes", label: "Proyectos recientes", icon: FolderKanban },
]

const appSections = {
  chat: { name: "Chat", contextual: "Conversaciones", icon: MessageSquare },
  dashboard: { name: "Dashboard", contextual: "Analítica", icon: ChartNoAxesColumnIncreasing },
  projects: { name: "Proyectos", contextual: "Proyectos", icon: FolderKanban },
  library: { name: "Biblioteca", contextual: "Biblioteca", icon: BookOpen },
  settings: { name: "Configuración", contextual: "Configuración", icon: Settings },
} as const satisfies Record<Destination, { name: string; contextual: string; icon: typeof MessageSquare }>

const primarySections = ["chat", "dashboard", "projects", "library"] as const

function Rail({ section }: { section: Destination }) {
  const { isMobile, open, openMobile, toggleSidebar } = useSidebar()
  const panelOpen = isMobile ? openMobile : open
  const route = (id: Destination) => {
    const { name, icon: Icon } = appSections[id]
    return (
      <SidebarMenuItem key={id}>
        <SidebarMenuButton
          className="rail-link"
          render={<a href={`#${id}`} />}
          isActive={id === section}
          aria-current={id === section ? "page" : undefined}
          aria-label={name}
          title={name}
        >
          <Icon />
        </SidebarMenuButton>
      </SidebarMenuItem>
    )
  }

  return (
    <Sidebar collapsible="none" className="navigation-rail">
      <SidebarHeader className="rail-brand">
        <div className="brand-mark" role="img" aria-label="Design Skills Router"><Route size={21} /></div>
      </SidebarHeader>
      <SidebarContent className="rail-body">
        <nav className="rail-nav" aria-label="Navegación principal">
          <SidebarMenu className="rail-primary">{primarySections.map(route)}</SidebarMenu>
          <SidebarMenu className="rail-secondary">
            {route("settings")}
            <SidebarMenuItem>
              <Button
                className="rail-toggle"
                size="icon"
                variant="ghost"
                onClick={toggleSidebar}
                aria-expanded={panelOpen}
                aria-controls={panelOpen ? "desktop-context-content" : undefined}
                aria-haspopup={isMobile ? "dialog" : undefined}
                aria-label={panelOpen ? "Ocultar panel contextual" : "Mostrar panel contextual"}
                title={panelOpen ? "Ocultar panel contextual" : "Mostrar panel contextual"}
              >
                {panelOpen ? <PanelLeftClose /> : <PanelLeftOpen />}
              </Button>
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
  icon: typeof FileText
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
              <Icon /><span className="context-row-main">{item.name}</span>
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
          <Button variant="ghost" size="icon" aria-label="Cerrar panel contextual" onClick={() => setOpenMobile(false)}><X /></Button>
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
  children,
}: {
  section: Destination
  theme: "light" | "dark"
  onTheme: () => void
  context: ReactNode
  children: ReactNode
}) {
  const { isMobile, open } = useSidebar()
  const [initialWidth] = useState(readSidebarWidth)
  const sidebarWidth = useRef(initialWidth)
  const contextualPanel = <ContextContents section={section}>{context}</ContextContents>

  return (
    <>
      <Rail section={section} />
      {isMobile && <Sidebar>{contextualPanel}</Sidebar>}
      <ResizablePanelGroup
        className="shell-panels"
        orientation="horizontal"
        resizeTargetMinimumSize={{ fine: 12, coarse: 24 }}
      >
        {!isMobile && open && (
          <ResizablePanel
            key="context"
            id="resizable-context"
            defaultSize={sidebarWidth.current}
            minSize={sidebarRange.minimum}
            maxSize={sidebarRange.maximum}
            groupResizeBehavior="preserve-pixel-size"
            onResize={(size, _id, previous) => {
              if (previous && size.inPixels >= sidebarRange.minimum - 0.5 && size.inPixels <= sidebarRange.maximum + 0.5) {
                const width = Math.min(sidebarRange.maximum, Math.max(sidebarRange.minimum, Math.round(size.inPixels)))
                sidebarWidth.current = width
                writePreference("sidebar-width", String(width))
              }
            }}
          >
            <Sidebar collapsible="none" className="desktop-context">{contextualPanel}</Sidebar>
          </ResizablePanel>
        )}
        {!isMobile && open && <ResizableHandle key="handle" aria-label="Redimensionar panel contextual" className="context-separator" />}
        <ResizablePanel key="workspace" id="resizable-workspace">
          <SidebarInset className="workspace">
            <header className="workspace-toolbar">
              <div className="workspace-location">
                <span className="location-root">Pizarra</span>
                <ChevronRight aria-hidden="true" className="location-chevron" />
                <strong>{appSections[section].name}</strong>
              </div>
              <div className="toolbar-actions">
                <Badge variant="outline" className="demo-badge"><span aria-hidden="true" />Demo local</Badge>
                <Button
                  size="icon"
                  variant="outline"
                  className="theme-toggle"
                  onClick={onTheme}
                  aria-label={theme === "light" ? "Activar tema oscuro" : "Activar tema claro"}
                  title={theme === "light" ? "Activar tema oscuro" : "Activar tema claro"}
                >
                  {theme === "light" ? <Moon /> : <Sun />}
                </Button>
              </div>
            </header>
            {children}
          </SidebarInset>
        </ResizablePanel>
      </ResizablePanelGroup>
    </>
  )
}

function ThemeSettings({ theme, onTheme }: { theme: "light" | "dark"; onTheme: (theme: "light" | "dark") => void }) {
  return (
    <div className="standard-view" id="apariencia">
      <header className="page-heading"><div><h1>Preferencias del espacio</h1><p>Ajusta la apariencia de la pizarra en este navegador.</p></div></header>
      <Card className="detail-card">
        <CardHeader><CardTitle><h2>Tema de la interfaz</h2></CardTitle><CardDescription>El cambio se aplica a todas las vistas.</CardDescription></CardHeader>
        <CardContent>
          <ToggleGroup variant="outline" aria-label="Tema de la interfaz" value={[theme]} onValueChange={values => {
            if (values[0] === "light" || values[0] === "dark") onTheme(values[0])
          }}>
            <ToggleGroupItem value="light"><Sun /> Claro</ToggleGroupItem>
            <ToggleGroupItem value="dark"><Moon /> Oscuro</ToggleGroupItem>
          </ToggleGroup>
        </CardContent>
      </Card>
    </div>
  )
}

function ResourceView({
  section,
  selected,
  onSelect,
}: {
  section: "projects" | "library"
  selected: string
  onSelect: (id: string) => void
}) {
  const items = section === "projects" ? projects : documents
  const item = items.find(entry => entry.id === selected) ?? items[0]
  const project = projects.find(entry => entry.id === item.id)
  return (
    <div className="standard-view">
      <header className="page-heading">
        <div><h1>{item.name}</h1><p>{item.area} · Contenido de ejemplo</p></div>
      </header>
      <Card className="detail-card">
        <CardHeader>
          <CardTitle><h2>{section === "projects" ? "Acerca del proyecto" : "Resumen del documento"}</h2></CardTitle>
          <CardDescription>{item.detail}</CardDescription>
        </CardHeader>
        {project && (
          <CardContent className="project-progress">
            <ProjectStatus status={project.status} />
            <label htmlFor="project-progress">Avance de ejemplo <strong>{project.progress} %</strong></label>
            <progress id="project-progress" value={project.progress} max={100} />
          </CardContent>
        )}
      </Card>
      <SidebarGroupLabel className="related-label">{section === "projects" ? "Explorar proyectos" : "Explorar documentos"}</SidebarGroupLabel>
      <div className="related-resources">
        {items.filter(entry => entry.id !== item.id).map(entry => (
          <Button key={entry.id} variant="outline" onClick={() => onSelect(entry.id)}>
            {section === "projects" ? <Folder data-icon="inline-start" /> : <FileText data-icon="inline-start" />}
            {entry.name}
          </Button>
        ))}
      </div>
    </div>
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
  const { isMobile, setOpenMobile } = useSidebar()
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

  function createThread() {
    const next: Conversation = { id: crypto.randomUUID(), title: "Nueva conversación", date: "Ahora", messages: [] }
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
              <SidebarMenuButton className="context-row" isActive={id === dashboardAnchor} onClick={() => {
                selectDashboardAnchor(id)
                closeMobilePanel()
                document.getElementById(id)?.scrollIntoView({ block: "start" })
              }}><Icon /><span>{label}</span></SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroup>
    ),
    projects: <ResourceList label="Proyectos del espacio" items={projects} selected={project} icon={Folder} onSelect={id => { selectProject(id); closeMobilePanel() }} />,
    library: <ResourceList label="Documentos" items={documents} selected={documentId} icon={FileText} onSelect={id => { selectDocument(id); closeMobilePanel() }} />,
    settings: <ResourceList label="Preferencias" items={[{ id: "apariencia", name: "Apariencia" }]} selected="apariencia" icon={Circle} onSelect={id => {
      closeMobilePanel()
      document.getElementById(id)?.scrollIntoView({ block: "start" })
    }} />,
  }

  const views = {
    chat: <ChatView conversation={thread} draft={drafts[thread.id] ?? ""} onDraft={setDraft} onSend={sendMessage} />,
    dashboard: <DashboardView period={period} onPeriod={setPeriod} onProject={id => { selectProject(id); window.location.hash = "projects" }} />,
    projects: <ResourceView section="projects" selected={project} onSelect={selectProject} />,
    library: <ResourceView section="library" selected={documentId} onSelect={selectDocument} />,
    settings: <ThemeSettings theme={theme} onTheme={onTheme} />,
  }

  return (
    <WorkspaceLayout section={section} theme={theme} onTheme={() => onTheme(theme === "light" ? "dark" : "light")} context={contexts[section]}>
      {section === "chat"
        ? views.chat
        : <div className="workspace-scroll" key={section}><Suspense fallback={<p className="view-loading" role="status">Cargando el dashboard…</p>}>{views[section]}</Suspense></div>}
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
