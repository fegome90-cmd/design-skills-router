import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, test } from "vitest"
import { agent, registerAppWebMCP, setAgentConfirmHandler } from "@/agent"
import { App } from "@/app"

beforeEach(() => {
  window.localStorage.clear()
  window.location.hash = ""
  document.documentElement.classList.remove("dark")
  document.documentElement.style.colorScheme = "light"
  delete document.documentElement.dataset.density
  setAgentConfirmHandler(null)
})

describe("Pizarra Desktop Demo", () => {
  test("an agent can inspect every visible control and act across all views including data-agent-confirm", async () => {
    render(<App />)

    const components = agent
      .snapshot()
      .filter((entry) => !entry.offPage && entry.component !== "more")
    expect(components.length).toBeGreaterThan(0)

    for (const entry of components) {
      expect(entry.label, `${entry.component} ${entry.ref} has no name`).toBeTruthy()
    }

    const labels = components.map((entry) => entry.label)
    for (const expected of [
      "Chat",
      "Dashboard",
      "Proyectos",
      "Biblioteca",
      "Configuración",
      "Ocultar panel contextual",
      "Nueva conversación",
      "Buscar conversaciones",
      "Escribe un mensaje",
      "Enviar mensaje",
      "Comandos",
      "Agente UI",
      "Activar tema oscuro",
    ]) {
      expect(labels, `${expected} is missing from the snapshot`).toContain(expected)
    }

    const searchResult = await agent.act({
      steps: [{ ref: "Buscar conversaciones", action: "setValue", args: ["referencias"] }],
    })
    expect(searchResult.ok, searchResult.error?.message).toBe(true)
    expect(screen.getByRole("button", { name: "Lectura de referencias" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Diseño de la pizarra" })).not.toBeInTheDocument()

    const chatResult = await agent.act({
      steps: [
        { ref: "Nueva conversación", action: "press" },
        { ref: "Escribe un mensaje", action: "setValue", args: ["Hola desde el agente"] },
        { ref: "Enviar mensaje", action: "press" },
        { ref: "Activar tema oscuro", action: "press" },
      ],
    })
    expect(chatResult.ok, chatResult.error?.message).toBe(true)
    expect(screen.getByRole("log")).toHaveTextContent("Hola desde el agente")
    expect(document.documentElement).toHaveClass("dark")

    const navDashboard = await agent.act({
      steps: [{ ref: "Dashboard", action: "press" }],
    })
    expect(navDashboard.ok, navDashboard.error?.message).toBe(true)
    await screen.findByRole("heading", { name: "Resumen del espacio" })

    const periodResult = await agent.act({
      steps: [{ ref: "7 días", action: "setPressed", args: [true] }],
    })
    expect(periodResult.ok, periodResult.error?.message).toBe(true)
    expect(screen.getByTestId("metric-conversations")).toHaveTextContent("36")

    const projectsNav = agent
      .snapshot()
      .find((entry) => !entry.offPage && entry.label === "Proyectos" && entry.actions.includes("press"))
    expect(projectsNav).toBeDefined()
    const navProjects = await agent.act({
      steps: [{ ref: projectsNav!.ref, action: "press" }],
    })
    expect(navProjects.ok, navProjects.error?.message).toBe(true)
    expect(screen.getByRole("heading", { name: "Pizarra React" })).toBeInTheDocument()

    const sliderResult = await agent.act({
      steps: [
        { ref: "Secciones del proyecto", action: "setValue", args: ["simulador"] },
        { ref: "Simular avance del proyecto", action: "setValue", args: [90] },
      ],
    })
    expect(sliderResult.ok, sliderResult.error?.message).toBe(true)
    expect(screen.getByRole("slider", { name: "Simular avance del proyecto" })).toHaveValue("90")

    let approve = false
    setAgentConfirmHandler(() => approve)

    const refusedConfirm = await agent.act({
      steps: [{ ref: "Restablecer avance", action: "press", args: ["Restablecer"] }],
    })
    expect(refusedConfirm.ok).toBe(false)
    expect(screen.getByRole("slider", { name: "Simular avance del proyecto" })).toHaveValue("90")

    approve = true
    const approvedConfirm = await agent.act({
      steps: [{ ref: "Restablecer avance", action: "press", args: ["Restablecer"] }],
    })
    expect(approvedConfirm.ok, approvedConfirm.error?.message).toBe(true)
    expect(screen.getByRole("slider", { name: "Simular avance del proyecto" })).toHaveValue("72")

    const libraryNav = agent
      .snapshot()
      .find((entry) => !entry.offPage && entry.label === "Biblioteca" && entry.actions.includes("press"))
    expect(libraryNav).toBeDefined()
    const libraryResult = await agent.act({
      steps: [
        { ref: libraryNav!.ref, action: "press" },
        { ref: "Mapa de documentación", action: "setValue", args: ["tokens"] },
      ],
    })
    expect(libraryResult.ok, libraryResult.error?.message).toBe(true)
    expect(screen.getByRole("heading", { name: "Tokens de superficie" })).toBeInTheDocument()

    const settingsNav = agent
      .snapshot()
      .find((entry) => !entry.offPage && entry.label === "Configuración" && entry.actions.includes("press"))
    expect(settingsNav).toBeDefined()
    const settingsResult = await agent.act({
      steps: [
        { ref: settingsNav!.ref, action: "press" },
        { ref: "Claro", action: "setPressed", args: [true] },
        { ref: "Densidad de la interfaz", action: "setValue", args: ["compact"] },
        { ref: "Notificaciones emergentes", action: "setChecked", args: [false] },
      ],
    })
    expect(settingsResult.ok, settingsResult.error?.message).toBe(true)
    expect(screen.getByRole("heading", { name: "Preferencias del espacio" })).toBeInTheDocument()
    expect(document.documentElement).not.toHaveClass("dark")
    expect(document.documentElement.dataset.density).toBe("compact")
    expect(screen.getByRole("switch", { name: "Notificaciones emergentes" })).toHaveAttribute("aria-checked", "false")
  })

  test("registerAppWebMCP exposes snapshot, act, and query via WebMCP", async () => {
    const tools = new Map<string, { execute: (input: object) => Promise<unknown> | unknown }>()
    const descriptor = Object.getOwnPropertyDescriptor(document, "modelContext")

    Object.defineProperty(document, "modelContext", {
      configurable: true,
      writable: true,
      value: {
        registerTool: async (tool: {
          name: string
          execute: (input: object) => Promise<unknown> | unknown
        }) => {
          tools.set(tool.name, tool)
        },
      },
    })

    let unregister: (() => void) | undefined
    try {
      unregister = registerAppWebMCP()
      expect([...tools.keys()]).toEqual(expect.arrayContaining(["snapshot", "act", "query"]))

      render(<App />)
      const snapshot = await tools.get("snapshot")!.execute({})
      expect(Array.isArray(snapshot)).toBe(true)
      expect((snapshot as unknown[]).length).toBeGreaterThan(0)
    } finally {
      unregister?.()
      if (descriptor) {
        Object.defineProperty(document, "modelContext", descriptor)
      } else {
        delete (document as { modelContext?: unknown }).modelContext
      }
    }
  })

  test("supports CommandPalette, AgentDrawer, ProjectsView, LibraryView, SettingsView, and Mod+B", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "Comandos" }))
    const commandDialog = await screen.findByRole("dialog", { name: "Paleta de comandos" })
    expect(commandDialog).toBeInTheDocument()
    const commandInput = screen.getByRole("combobox", { name: "Buscar comando" })
    await user.type(commandInput, "Dashboard")
    const dashboardOption = screen.getByRole("option", { name: /Dashboard/i })
    await user.click(dashboardOption)
    await screen.findByRole("heading", { name: "Resumen del espacio" })

    await user.click(screen.getByRole("button", { name: "Agente UI" }))
    expect(await screen.findByRole("heading", { name: "Agente UI · WebMCP" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Flujos" })).toBeInTheDocument()
    await user.click(screen.getByRole("tab", { name: "Snapshot" }))
    expect(screen.getByRole("textbox", { name: "Filtrar snapshot" })).toBeInTheDocument()
    await user.click(screen.getByRole("tab", { name: "Eventos" }))
    expect(screen.getByRole("button", { name: "Limpiar eventos" })).toBeInTheDocument()
    await user.click(screen.getByRole("tab", { name: "Flujos" }))
    await user.click(screen.getByRole("button", { name: "Cerrar inspector del agente" }))

    await user.click(screen.getByRole("link", { name: "Proyectos" }))
    expect(screen.getByRole("heading", { name: "Pizarra React" })).toBeInTheDocument()
    await user.click(screen.getByRole("tab", { name: "Simulador" }))
    const slider = screen.getByRole("slider", { name: "Simular avance del proyecto" })
    slider.focus()
    await user.keyboard("{ArrowRight}")
    expect(slider).toHaveValue("73")

    await user.click(screen.getByRole("button", { name: "Restablecer avance" }))
    const alertDialog = await screen.findByRole("alertdialog", { name: "¿Restablecer el avance simulado?" })
    expect(alertDialog).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Restablecer" }))
    await waitFor(() => {
      expect(screen.getByRole("slider", { name: "Simular avance del proyecto" })).toHaveValue("72")
    })

    await user.click(screen.getByRole("link", { name: "Biblioteca" }))
    expect(screen.getByRole("heading", { name: "Patrones de navegación" })).toBeInTheDocument()
    await user.click(screen.getByRole("treeitem", { name: "Casos de interacción" }))
    expect(screen.getByRole("heading", { name: "Casos de interacción" })).toBeInTheDocument()

    await user.click(screen.getByRole("link", { name: "Configuración" }))
    expect(screen.getByRole("heading", { name: "Preferencias del espacio" })).toBeInTheDocument()
    await user.click(screen.getByRole("combobox", { name: "Densidad de la interfaz" }))
    await user.click(screen.getByRole("option", { name: "Compacta" }))
    expect(document.documentElement.dataset.density).toBe("compact")

    const notificationsSwitch = screen.getByRole("switch", { name: "Notificaciones emergentes" })
    await user.click(notificationsSwitch)
    expect(notificationsSwitch).toHaveAttribute("aria-checked", "false")

    const modB = /Mac|iPhone|iPad|iPod/.test(navigator.platform || navigator.userAgent)
      ? "{Meta>}b{/Meta}"
      : "{Control>}b{/Control}"

    expect(screen.getByRole("complementary", { name: "Panel contextual" })).toBeInTheDocument()
    await user.keyboard(modB)
    await waitFor(() => {
      expect(screen.queryByRole("complementary", { name: "Panel contextual" })).not.toBeInTheDocument()
    })
    expect(screen.getByRole("button", { name: "Mostrar panel contextual" })).toBeInTheDocument()

    await user.keyboard(modB)
    await waitFor(() => {
      expect(screen.getByRole("complementary", { name: "Panel contextual" })).toBeInTheDocument()
    })
  })
})
