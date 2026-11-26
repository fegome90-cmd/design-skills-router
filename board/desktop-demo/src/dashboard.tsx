import { ArrowUpRight, File, Folder, ListChecks, MessageSquare } from "lucide-react"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import { ProjectStatus } from "@/components/project-status"
import { Button } from "@ui-sdk/react/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Toggle, ToggleGroup } from "@ui-sdk/react/toggle"
import { activity, metrics, periods, projects, type Period } from "@/data"

const metricLabels = [
  { name: "Conversaciones", key: "conversations", icon: MessageSquare, note: "Hilos iniciados" },
  { name: "Proyectos", key: "projects", icon: Folder, note: "Con actividad" },
  { name: "Recursos", key: "resources", icon: File, note: "Añadidos a la biblioteca" },
  { name: "Revisiones", key: "reviews", icon: ListChecks, note: "Completadas" },
] as const

const chartConfig = {
  conversations: { label: "Conversaciones", color: "var(--chart-1)" },
  reviews: { label: "Revisiones", color: "var(--chart-2)" },
} satisfies ChartConfig

export default function DashboardView({
  period,
  onPeriod,
  onProject,
}: {
  period: Period
  onPeriod: (value: Period) => void
  onProject: (id: string) => void
}) {
  const series = activity[period].map(([date, conversations, reviews]) => ({ date, conversations, reviews }))

  return (
    <div className="dashboard-view" id="resumen">
      <header className="page-heading">
        <div>
          <h1>Resumen del espacio</h1>
          <p>Conversaciones, proyectos y recursos de la pizarra.</p>
        </div>
        <ToggleGroup
          className="periods"
          data-size="sm"
          deselectable={false}
          aria-label="Período"
          value={[String(period)]}
          onValueChange={(values: string[]) => {
            const selected = periods.find(option => String(option) === values[0])
            if (selected) onPeriod(selected)
          }}
        >
          {periods.map(option => <Toggle key={option} value={String(option)} data-size="sm">{option} días</Toggle>)}
        </ToggleGroup>
      </header>

      <div className="metric-grid">
        {metricLabels.map(({ key, name, icon: Icon, note }) => (
          <Card className="metric-card" key={key}>
            <CardHeader>
              <CardDescription>{name}</CardDescription>
              <CardAction className="metric-icon"><Icon aria-hidden="true" /></CardAction>
              <CardTitle data-testid={`metric-${key}`}>{metrics[period][key]}</CardTitle>
            </CardHeader>
            <CardContent className="metric-note">{note}</CardContent>
          </Card>
        ))}
      </div>

      <Card className="activity-card" id="actividad">
        <CardHeader>
          <CardTitle><h2>{period === 7 ? "Actividad semanal" : "Actividad del espacio"}</h2></CardTitle>
          <CardDescription>Conversaciones iniciadas y revisiones completadas</CardDescription>
          <CardAction>
            <div className="chart-key">
              <span><i className="chart-dot" aria-hidden="true" />Conversaciones</span>
              <span><i className="chart-dot chart-dot-secondary" aria-hidden="true" />Revisiones</span>
            </div>
          </CardAction>
        </CardHeader>
        <CardContent>
          <ChartContainer className="activity-chart" config={chartConfig}>
            <BarChart accessibilityLayer data={series} margin={{ top: 10, right: 5, left: 0 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 4" />
              <XAxis dataKey="date" tick={{ fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} tickMargin={10} minTickGap={20} />
              <YAxis allowDecimals={false} tick={{ fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} width={25} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="conversations" fill="var(--color-conversations)" radius={[3, 3, 0, 0]} maxBarSize={22} isAnimationActive={false} />
              <Bar dataKey="reviews" fill="var(--color-reviews)" radius={[3, 3, 0, 0]} maxBarSize={22} isAnimationActive={false} />
            </BarChart>
          </ChartContainer>
        </CardContent>
      </Card>

      <Card className="project-table" id="proyectos-recientes">
        <CardHeader>
          <CardTitle><h2>Proyectos recientes</h2></CardTitle>
          <CardDescription>Actividad de ejemplo de los proyectos del espacio</CardDescription>
        </CardHeader>
        <CardContent>
          <Table aria-label="Proyectos recientes">
            <TableHeader>
              <TableRow>
                <TableHead>Proyecto</TableHead><TableHead>Área</TableHead><TableHead>Estado</TableHead><TableHead>Actualizado</TableHead><TableHead><span className="sr-only">Abrir</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {projects.map(project => (
                <TableRow key={project.id}>
                  <TableCell className="font-medium">{project.name}</TableCell>
                  <TableCell>{project.area}</TableCell>
                  <TableCell><ProjectStatus status={project.status} /></TableCell>
                  <TableCell>{project.date}</TableCell>
                  <TableCell className="text-right">
                    <Button data-variant="ghost" data-size="icon-sm" aria-label={`Abrir proyecto ${project.name}`} title={`Abrir ${project.name}`} onClick={() => onProject(project.id)}>
                      <ArrowUpRight aria-hidden="true" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
