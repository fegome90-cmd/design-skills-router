import {
  Accordion,
  AccordionHeader,
  AccordionItem,
  AccordionPanel,
  AccordionTrigger,
} from "@ui-sdk/react/accordion"
import {
  AlertDialog,
  AlertDialogBackdrop,
  AlertDialogClose,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@ui-sdk/react/alert-dialog"
import { Field, FieldDescription, FieldLabel } from "@ui-sdk/react/field"
import {
  Progress,
  ProgressIndicator,
  ProgressLabel,
  ProgressTrack,
  ProgressValue,
} from "@ui-sdk/react/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectItemIndicator,
  SelectTrigger,
  SelectValue,
} from "@ui-sdk/react/select"
import {
  Slider,
  SliderControl,
  SliderIndicator,
  SliderThumb,
  SliderTrack,
  SliderValue,
} from "@ui-sdk/react/slider"
import { Switch, SwitchThumb } from "@ui-sdk/react/switch"
import {
  Tabs,
  TabsIndicator,
  TabsList,
  TabsPanel,
  TabsTab,
} from "@ui-sdk/react/tabs"
import {
  Tree,
  TreeGroup,
  TreeItem,
  TreeItemIndicator,
  TreeItemLabel,
} from "@ui-sdk/react/tree"
import {
  Check,
  ChevronDown,
  ChevronRight,
  File,
  Folder,
  Moon,
  RotateCcw,
  Sun,
} from "lucide-react"
import { useLayoutEffect, useRef, useState } from "react"
import { ProjectStatus } from "@/components/project-status"
import { Button } from "@ui-sdk/react/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { SidebarGroupLabel } from "@/components/ui/sidebar"
import { Toggle, ToggleGroup } from "@ui-sdk/react/toggle"
import { documents, projects } from "@/data"
import { sidebarRange } from "@/preferences"

const densityOptions = [
  { value: "comfortable", label: "Cómoda" },
  { value: "compact", label: "Compacta" },
]

function projectMilestones(project: (typeof projects)[number]) {
  return [
    {
      value: "arquitectura",
      title: "Arquitectura y límites del espacio",
      body: `Define el reparto entre el carril fijo, el panel contextual y el área principal de ${project.name} (${project.area}).`,
    },
    {
      value: "primitivas",
      title: "Primitivas e interacciones",
      body: `Integra controles accesibles con soporte completo de teclado, atributos ARIA y foco predecible para ${project.name}.`,
    },
    {
      value: "verificacion",
      title: "Verificación y criterios de entrega",
      body: `${project.detail} Estado actual: ${project.status} (${project.date}).`,
    },
  ]
}

export function ProjectsView({
  projectId,
  onSelectProject,
  onNotify,
}: {
  projectId: string
  onSelectProject: (id: string) => void
  onNotify?: (message: string) => void
}) {
  const project = projects.find((entry) => entry.id === projectId) ?? projects[0]
  const projectHeading = useRef<HTMLHeadingElement>(null)
  const focusHeading = useRef(false)
  const [progressByProject, setProgressByProject] = useState<
    Record<string, number>
  >({})
  const simulatedProgress = progressByProject[project.id] ?? project.progress

  useLayoutEffect(() => {
    if (!focusHeading.current) return
    focusHeading.current = false
    projectHeading.current?.focus()
  }, [project.id])

  function setSimulatedProgress(value: number) {
    setProgressByProject((prev) => ({ ...prev, [project.id]: value }))
  }

  const milestones = projectMilestones(project)

  return (
    <div className="standard-view">
      <header className="page-heading">
        <div>
          <h1 ref={projectHeading} tabIndex={-1}>{project.name}</h1>
          <p>{project.area} · Contenido de ejemplo</p>
        </div>
      </header>

      <Tabs defaultValue="resumen">
        <TabsList aria-label="Secciones del proyecto">
          <TabsTab value="resumen">Resumen</TabsTab>
          <TabsTab value="simulador">Simulador</TabsTab>
          <TabsTab value="hitos">Hitos</TabsTab>
          <TabsIndicator />
        </TabsList>

        <TabsPanel value="resumen">
          <Card className="detail-card">
            <CardHeader>
              <CardTitle>
                <h2>Acerca del proyecto</h2>
              </CardTitle>
              <CardDescription>{project.detail}</CardDescription>
            </CardHeader>
            <CardContent className="project-progress">
              <ProjectStatus status={project.status} />
              <Progress
                value={simulatedProgress}
                min={0}
                max={100}
                className="project-progress-root"
              >
                <div className="project-progress-meta col-span-full flex w-full items-center justify-between text-xs text-muted-foreground">
                  <ProgressLabel>Avance de ejemplo</ProgressLabel>
                  <ProgressValue>
                    {() => <strong>{simulatedProgress} %</strong>}
                  </ProgressValue>
                </div>
                <ProgressTrack className="h-2.5 bg-muted">
                  <ProgressIndicator className="bg-primary" />
                </ProgressTrack>
              </Progress>
            </CardContent>
          </Card>
        </TabsPanel>

        <TabsPanel value="simulador">
          <Card className="detail-card">
            <CardHeader>
              <CardTitle>
                <h2>Simulador de avance</h2>
              </CardTitle>
              <CardDescription>
                Ajusta el porcentaje local del proyecto o restablece el valor
                inicial.
              </CardDescription>
            </CardHeader>
            <CardContent className="project-controls">
              <Field>
                <Slider
                  min={0}
                  max={100}
                  step={1}
                  value={simulatedProgress}
                  onValueChange={(value) =>
                    setSimulatedProgress(Array.isArray(value) ? value[0] : value)
                  }
                >
                  <div className="project-control-bar">
                    <FieldLabel>Simular avance del proyecto</FieldLabel>
                    <SliderValue>
                      {() => <span>{simulatedProgress} %</span>}
                    </SliderValue>
                  </div>
                  <SliderControl>
                    <SliderTrack>
                      <SliderIndicator />
                      <SliderThumb aria-label="Simular avance del proyecto" />
                    </SliderTrack>
                  </SliderControl>
                </Slider>
              </Field>

              <div className="project-control-bar">
                <span className="settings-row-desc">
                  Valor inicial de {project.name}: {project.progress} %
                </span>
                <AlertDialog>
                  <AlertDialogTrigger>
                    <RotateCcw className="size-3.5" aria-hidden="true" />
                    Restablecer avance
                  </AlertDialogTrigger>
                  <AlertDialogBackdrop />
                  <AlertDialogContent>
                    <AlertDialogTitle>
                      ¿Restablecer el avance simulado?
                    </AlertDialogTitle>
                    <AlertDialogDescription>
                      Volverá al valor inicial del proyecto ({project.progress}{" "}
                      %).
                    </AlertDialogDescription>
                    <div className="alert-dialog-actions">
                      <AlertDialogClose>Cancelar</AlertDialogClose>
                      <AlertDialogClose
                        value="confirm"
                        data-variant="destructive"
                        data-agent-confirm={`Restablece el avance de ${project.name} a ${project.progress} %`}
                        action={() => {
                          setSimulatedProgress(project.progress)
                          onNotify?.(
                            `Avance restablecido a ${project.progress} %`
                          )
                        }}
                      >
                        Restablecer
                      </AlertDialogClose>
                    </div>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </CardContent>
          </Card>
        </TabsPanel>

        <TabsPanel value="hitos">
          <Card className="detail-card">
            <CardHeader>
              <CardTitle>
                <h2>Hitos y decisiones</h2>
              </CardTitle>
              <CardDescription>
                Fases principales registradas para {project.name}.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Accordion defaultValue={["arquitectura"]} multiple>
                {milestones.map((item) => (
                  <AccordionItem key={item.value} value={item.value}>
                    <AccordionHeader>
                      <AccordionTrigger>
                        {item.title}
                        <ChevronDown
                          aria-hidden="true"
                          className="size-4 shrink-0 text-muted-foreground transition-transform [[data-open]>&]:rotate-180"
                        />
                      </AccordionTrigger>
                    </AccordionHeader>
                    <AccordionPanel>
                      <p>{item.body}</p>
                    </AccordionPanel>
                  </AccordionItem>
                ))}
              </Accordion>
            </CardContent>
          </Card>
        </TabsPanel>
      </Tabs>

      <SidebarGroupLabel className="related-label">
        Explorar proyectos
      </SidebarGroupLabel>
      <div className="related-resources">
        {projects
          .filter((entry) => entry.id !== project.id)
          .map((entry) => (
            <Button
              key={entry.id}
              onClick={() => {
                focusHeading.current = true
                onSelectProject(entry.id)
              }}
            >
              <Folder data-icon="inline-start" aria-hidden="true" />
              {entry.name}
            </Button>
          ))}
      </div>
    </div>
  )
}

export function LibraryView({
  documentId,
  onSelectDocument,
}: {
  documentId: string
  onSelectDocument: (id: string) => void
}) {
  const activeDocument =
    documents.find((entry) => entry.id === documentId) ?? documents[0]
  const documentHeading = useRef<HTMLHeadingElement>(null)
  const focusHeading = useRef(false)

  useLayoutEffect(() => {
    if (!focusHeading.current) return
    focusHeading.current = false
    documentHeading.current?.focus()
  }, [activeDocument.id])

  const treeGroups = [
    {
      value: "grupo-referencias",
      label: "Referencias visuales",
      docs: documents.filter((doc) => doc.area === "Referencias visuales"),
    },
    {
      value: "grupo-sistema",
      label: "Sistema visual",
      docs: documents.filter((doc) => doc.area === "Sistema visual"),
    },
    {
      value: "grupo-verificacion",
      label: "Verificación",
      docs: documents.filter((doc) => doc.area === "Verificación"),
    },
  ]

  function handleDocumentSelection(value: string | null) {
    if (value && documents.some((entry) => entry.id === value)) {
      onSelectDocument(value)
    }
  }

  return (
    <div className="standard-view">
      <header className="page-heading">
        <div>
          <h1 ref={documentHeading} tabIndex={-1}>{activeDocument.name}</h1>
          <p>{activeDocument.area} · Contenido de ejemplo</p>
        </div>
      </header>

      <Card className="detail-card">
        <CardHeader>
          <CardTitle>
            <h2>Nota de referencia</h2>
          </CardTitle>
          <CardDescription>{activeDocument.detail}</CardDescription>
        </CardHeader>
      </Card>

      <Card className="detail-card">
        <CardHeader>
          <CardTitle>
            <h2>Mapa de documentación</h2>
          </CardTitle>
          <CardDescription>
            Explora la jerarquía de guías y referencias del espacio de trabajo.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tree
            aria-label="Mapa de documentación"
            value={activeDocument.id}
            current={activeDocument.id}
            defaultExpanded={treeGroups.map((group) => group.value)}
            onValueChange={handleDocumentSelection}
            onAction={handleDocumentSelection}
          >
            {treeGroups.map((group) => (
              <TreeItem
                key={group.value}
                value={group.value}
                label={group.label}
              >
                <TreeItemLabel>
                  <TreeItemIndicator>
                    <ChevronRight className="size-4" aria-hidden="true" />
                  </TreeItemIndicator>
                  <Folder className="size-4" aria-hidden="true" />
                  <span>{group.label}</span>
                </TreeItemLabel>
                <TreeGroup>
                  {group.docs.map((doc) => (
                    <TreeItem key={doc.id} value={doc.id} label={doc.name}>
                      <TreeItemLabel>
                        <File className="size-4" aria-hidden="true" />
                        <span>{doc.name}</span>
                      </TreeItemLabel>
                    </TreeItem>
                  ))}
                </TreeGroup>
              </TreeItem>
            ))}
          </Tree>
        </CardContent>
      </Card>

      <SidebarGroupLabel className="related-label">
        Explorar documentos
      </SidebarGroupLabel>
      <div className="related-resources">
        {documents
          .filter((entry) => entry.id !== activeDocument.id)
          .map((entry) => (
            <Button
              key={entry.id}
              onClick={() => {
                focusHeading.current = true
                onSelectDocument(entry.id)
              }}
            >
              <File data-icon="inline-start" aria-hidden="true" />
              {entry.name}
            </Button>
          ))}
      </div>
    </div>
  )
}

export function SettingsView({
  theme,
  onThemeChange,
  density,
  onDensityChange,
  sidebarWidth,
  onSidebarWidthChange,
  toastsEnabled,
  onToastsChange,
}: {
  theme: "light" | "dark"
  onThemeChange: (theme: "light" | "dark") => void
  density: "comfortable" | "compact"
  onDensityChange: (density: "comfortable" | "compact") => void
  sidebarWidth: number
  onSidebarWidthChange: (width: number) => void
  toastsEnabled: boolean
  onToastsChange: (enabled: boolean) => void
}) {
  return (
    <div className="standard-view" id="apariencia">
      <header className="page-heading">
        <div>
          <h1>Preferencias del espacio</h1>
          <p>Ajustes locales de apariencia y distribución de ejemplo.</p>
        </div>
      </header>

      <Card className="detail-card">
        <CardHeader>
          <CardTitle>
            <h2>Apariencia y distribución</h2>
          </CardTitle>
          <CardDescription>
            Los cambios se aplican de inmediato en todas las vistas.
          </CardDescription>
        </CardHeader>
        <CardContent className="settings-rows">
          <div className="settings-row">
            <div className="settings-row-info">
              <span className="settings-row-title">Tema de la interfaz</span>
              <span className="settings-row-desc">
                Alterna entre superficie clara y superficie oscura.
              </span>
            </div>
            <ToggleGroup
              deselectable={false}
              aria-label="Tema de la interfaz"
              value={[theme]}
              onValueChange={(values: string[]) => {
                if (values[0] === "light" || values[0] === "dark") {
                  onThemeChange(values[0])
                }
              }}
            >
              <Toggle value="light">
                <Sun aria-hidden="true" /> Claro
              </Toggle>
              <Toggle value="dark">
                <Moon aria-hidden="true" /> Oscuro
              </Toggle>
            </ToggleGroup>
          </div>

          <Field className="settings-row flex-row">
            <div className="settings-row-info">
              <FieldLabel>Densidad de la interfaz</FieldLabel>
              <FieldDescription>
                Ajusta el espaciado vertical en tarjetas, hilos y listas.
              </FieldDescription>
            </div>
            <Select
              value={density}
              items={densityOptions}
              onValueChange={(value) => {
                if (value === "comfortable" || value === "compact") {
                  onDensityChange(value)
                }
              }}
            >
              <SelectTrigger className="w-44 shrink-0">
                <SelectValue placeholder="Selecciona densidad" />
                <ChevronDown aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
              </SelectTrigger>
              <SelectContent>
                {densityOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                    <SelectItemIndicator>
                      <Check className="size-4" aria-hidden="true" />
                    </SelectItemIndicator>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field>
            <Slider
              min={sidebarRange.minimum}
              max={sidebarRange.maximum}
              step={1}
              value={sidebarWidth}
              onValueChange={(value) =>
                onSidebarWidthChange(Array.isArray(value) ? value[0] : value)
              }
            >
              <div className="project-control-bar">
                <FieldLabel>Ancho del panel contextual</FieldLabel>
                <SliderValue>
                  {() => <span>{sidebarWidth} px</span>}
                </SliderValue>
              </div>
              <SliderControl>
                <SliderTrack>
                  <SliderIndicator />
                  <SliderThumb aria-label="Ancho del panel contextual" />
                </SliderTrack>
              </SliderControl>
            </Slider>
          </Field>

          <Field className="settings-row flex-row">
            <div className="settings-row-info">
              <FieldLabel>Notificaciones emergentes</FieldLabel>
              <FieldDescription>
                Muestra avisos breves al copiar respuestas o restablecer datos.
              </FieldDescription>
            </div>
            <Switch checked={toastsEnabled} onCheckedChange={onToastsChange}>
              <SwitchThumb />
            </Switch>
          </Field>
        </CardContent>
      </Card>
    </div>
  )
}
