import { expect, test } from "@playwright/test"
import { mkdir } from "node:fs/promises"
import { join } from "node:path"

test("the rail stays in place while the contextual panel changes and collapses", async ({ page }) => {
  await page.goto("/")
  const rail = page.getByRole("navigation", { name: "Navegación principal" })
  const context = page.getByRole("complementary", { name: "Panel contextual" })
  const railWidth = async () => (await page.locator(".navigation-rail").boundingBox())?.width
  await expect.poll(railWidth).toBe(64)
  await expect(rail.getByRole("link", { name: "Chat" })).toHaveAttribute("aria-current", "page")
  await expect(context.getByRole("heading", { name: "Conversaciones" })).toBeVisible()
  await rail.getByRole("link", { name: "Dashboard" }).click()
  await expect(context.getByRole("heading", { name: "Analítica" })).toBeVisible()
  await page.getByRole("button", { name: "Ocultar panel contextual" }).click()
  await expect(context).not.toBeVisible()
  await expect(rail).toBeVisible()
  await expect.poll(railWidth).toBe(64)
  await rail.getByRole("link", { name: "Proyectos" }).click()
  await expect(context).not.toBeVisible()
  await page.reload()
  await expect(context).not.toBeVisible()
  await page.getByRole("button", { name: "Mostrar panel contextual" }).click()
  await expect(context.getByRole("heading", { name: "Proyectos" })).toBeVisible()
  await rail.getByRole("link", { name: "Biblioteca" }).click()
  await expect(context.getByRole("heading", { name: "Biblioteca" })).toBeVisible()
  await rail.getByRole("link", { name: "Configuración" }).click()
  await expect(page.getByRole("heading", { name: "Preferencias del espacio" })).toBeVisible()
})

test("the sidebar resizes with pointer and keyboard and restores its width", async ({ page }) => {
  await page.goto("/")
  const panel = page.getByRole("complementary", { name: "Panel contextual" })
  const separator = page.getByRole("separator", { name: "Redimensionar panel contextual" })
  const before = (await panel.boundingBox())!.width
  const handle = (await separator.boundingBox())!
  const x = handle.x + handle.width / 2
  await page.mouse.move(x, 350)
  await page.mouse.down()
  await page.mouse.move(x + 34, 350, { steps: 8 })
  await page.mouse.up()
  await expect.poll(async () => (await panel.boundingBox())!.width).toBeGreaterThan(before + 20)
  await separator.focus()
  await expect(separator).toBeFocused()
  const pointerWidth = (await panel.boundingBox())!.width
  await page.keyboard.press("ArrowLeft")
  await expect.poll(async () => (await panel.boundingBox())!.width).toBeLessThan(pointerWidth)
  const savedWidth = (await panel.boundingBox())!.width
  await page.getByRole("button", { name: "Ocultar panel contextual" }).click()
  await page.getByRole("button", { name: "Mostrar panel contextual" }).click()
  await expect.poll(async () => Math.abs((await panel.boundingBox())!.width - savedWidth)).toBeLessThan(2)
  await page.reload()
  await expect.poll(async () => Math.abs((await panel.boundingBox())!.width - savedWidth)).toBeLessThan(2)
})

test("the sidebar keeps its width when browser storage cannot be written", async ({ page }) => {
  await page.addInitScript(() => {
    Storage.prototype.setItem = () => { throw new DOMException("Storage is read-only", "QuotaExceededError") }
  })
  await page.goto("/")
  const panel = page.getByRole("complementary", { name: "Panel contextual" })
  const width = async () => (await panel.boundingBox())!.width
  const before = await width()
  await page.getByRole("separator", { name: "Redimensionar panel contextual" }).press("ArrowRight")
  await expect.poll(width).toBeGreaterThan(before)
  const resized = await width()
  await page.getByRole("button", { name: "Ocultar panel contextual" }).click()
  await page.getByRole("button", { name: "Mostrar panel contextual" }).click()
  await expect.poll(async () => Math.abs(await width() - resized)).toBeLessThan(2)
})

test("Chat can search, create a conversation and keep its local messages across views", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByText("Conversación de ejemplo", { exact: true })).toBeVisible()
  await page.getByRole("searchbox", { name: "Buscar conversaciones" }).fill("referencias")
  await expect(page.getByRole("button", { name: "Lectura de referencias" })).toBeVisible()
  await expect(page.getByRole("button", { name: "Diseño de la pizarra" })).not.toBeVisible()
  await page.getByRole("button", { name: "Nueva conversación" }).click()
  await expect(page.getByRole("heading", { name: "Una conversación nueva" })).toBeVisible()
  await expect(page.getByText("Conversación local", { exact: true })).toBeVisible()
  const input = page.getByRole("textbox", { name: "Escribe un mensaje" })
  const send = page.getByRole("button", { name: "Enviar mensaje" })
  await expect(send).toBeDisabled()
  await expect(page.locator(".composer")).toHaveCSS("opacity", "1")
  await input.fill("Comprobación local del prototipo")
  await input.press("Enter")
  await expect(page.getByRole("log").getByText("Comprobación local del prototipo")).toBeVisible()
  await expect(page.getByRole("log").getByText("Asistente", { exact: true })).toHaveCount(0)
  await page.getByRole("link", { name: "Dashboard" }).click()
  await page.getByRole("link", { name: "Chat" }).click()
  await expect(page.getByRole("log").getByText("Comprobación local del prototipo")).toBeVisible()
})

test("Dashboard updates metrics and the chart when the period changes", async ({ page }) => {
  await page.goto("/#dashboard")
  await expect(page.getByRole("heading", { name: "Resumen del espacio" })).toBeVisible()
  const expectedMetrics = {
    conversations: { label: "Conversaciones", totals: { 7: 36, 30: 128, 90: 346 } },
    projects: { label: "Proyectos", totals: { 7: 4, 30: 12, 90: 23 } },
    resources: { label: "Recursos", totals: { 7: 12, 30: 48, 90: 114 } },
    reviews: { label: "Revisiones", totals: { 7: 8, 30: 24, 90: 63 } },
  } as const

  async function expectTotals(period: 7 | 30 | 90) {
    for (const [key, { label, totals }] of Object.entries(expectedMetrics)) {
      const card = page.locator(".metric-card").filter({ has: page.getByText(label, { exact: true }) })
      const total = expect(card.getByTestId(`metric-${key}`), `${label} total for ${period} days`)
      await total.toBeVisible()
      await total.toHaveText(String(totals[period]))
    }
  }

  const chart = page.locator("#actividad")
  const monthlyTick = chart.getByText("20 oct", { exact: true })
  await expectTotals(30)
  await expect(monthlyTick).toBeVisible()
  await page.getByRole("button", { name: "7 días" }).click()
  await expectTotals(7)
  await expect(page.getByRole("heading", { name: "Actividad semanal" })).toBeVisible()
  await expect(chart.getByText("Lun", { exact: true })).toBeVisible()
  await expect(monthlyTick).toHaveCount(0)
  await page.getByRole("button", { name: "90 días" }).click()
  await expectTotals(90)
})

test("Dashboard opens the details for the selected project row", async ({ page }) => {
  await page.goto("/#dashboard")
  const projects = page.getByRole("table", { name: "Proyectos recientes" })
  const row = projects.getByRole("row", { name: /Archivo de referencias/ })
  await row.getByRole("button", { name: "Abrir proyecto Archivo de referencias" }).click()
  await expect(page.getByRole("heading", { name: "Archivo de referencias", exact: true })).toBeVisible()
})

test("the theme works with keyboard and persists after reload", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" })
  await page.goto("/")
  const root = page.locator("html")
  const theme = page.getByRole("button", { name: "Activar tema oscuro" })
  await theme.focus()
  await page.keyboard.press("Enter")
  await expect(root).toHaveClass(/dark/)
  await page.reload()
  await expect(root).toHaveClass(/dark/)
  await page.getByRole("button", { name: "Activar tema claro" }).click()
  await expect(root).not.toHaveClass(/dark/)
})

test("at narrow widths the contextual dialog can be opened and escaped", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto("/")
  const trigger = page.getByRole("button", { name: "Mostrar panel contextual" })
  const dialog = page.getByRole("dialog")
  await trigger.click()
  await expect(dialog.getByRole("heading", { name: "Conversaciones" })).toBeVisible()
  await page.keyboard.press("Escape")
  await expect(dialog).not.toBeVisible()
  await expect(trigger).toBeFocused()
  await page.getByRole("link", { name: "Dashboard" }).click()
  await expect(page.getByRole("heading", { name: "Resumen del espacio" })).toBeVisible()
  const documentWidth = () => page.evaluate(() => document.documentElement.scrollWidth)
  expect(await documentWidth()).toBe(390)
  await page.setViewportSize({ width: 320, height: 680 })
  expect(await documentWidth()).toBe(320)

  const panel = page.getByRole("complementary", { name: "Panel contextual" })
  await page.setViewportSize({ width: 1024, height: 768 })
  await expect(panel.getByRole("heading", { name: "Analítica" })).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(panel).not.toBeVisible()
  await trigger.click()
  await expect(dialog.getByRole("heading", { name: "Analítica" })).toBeVisible()
})

test("UI SDK controls use the homepage palette and square geometry", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" })
  await page.goto("/#settings")

  const density = page.getByRole("combobox", { name: "Densidad de la interfaz" })
  await expect(density.locator("svg.lucide-chevron-down")).toBeVisible()
  await density.click()
  const selectedDensity = page.getByRole("option", { name: "Cómoda" })
  await expect(selectedDensity.locator('[data-slot="select-item-indicator"] svg.lucide-check')).toBeVisible()
  await page.keyboard.press("Escape")

  const notificationSwitch = page.getByRole("switch", { name: "Notificaciones emergentes" })
  await expect(notificationSwitch).toHaveCSS("border-radius", "0px")
  await expect(notificationSwitch).toHaveCSS("background-color", "rgb(10, 10, 10)")
  await expect(notificationSwitch.locator('[data-slot="switch-thumb"]')).toHaveCSS("border-radius", "0px")
  await notificationSwitch.click()
  await expect(notificationSwitch).toHaveCSS("background-color", "rgb(255, 255, 255)")

  await page.getByRole("button", { name: "Comandos" }).click()
  const palette = page.getByRole("dialog", { name: "Paleta de comandos" })
  await expect(palette).toHaveCSS("border-radius", "0px")
  await expect(palette).toHaveCSS("border-top-color", "rgb(10, 10, 10)")
  await expect(palette.locator("[data-highlighted]")).toHaveCSS("background-color", "rgb(10, 10, 10)")
  await expect(palette.locator(".command-search svg[aria-hidden='true']")).toBeVisible()
  const destinations = palette.getByRole("option")
  await expect(destinations).toHaveCount(6)
  for (const destination of await destinations.all()) {
    await expect(destination.locator('[data-slot="command-item-icon"] svg[aria-hidden="true"]')).toBeVisible()
  }
  await expect(palette.locator('[data-slot="command-empty"]')).toHaveCSS("padding-top", "0px")
  await page.keyboard.press("Escape")

  await page.getByRole("link", { name: "Proyectos" }).click()
  const simulator = page.getByRole("tab", { name: "Simulador" })
  await simulator.click()
  await expect(simulator).toHaveCSS("background-color", "rgb(10, 10, 10)")
  await expect(simulator).toHaveCSS("color", "rgb(255, 255, 255)")
  const thumb = page.locator('[data-slot="slider-thumb"]')
  await expect(thumb).toHaveCSS("border-radius", "0px")
  await expect(thumb).toHaveCSS("border-top-color", "rgb(10, 10, 10)")

  await page.getByRole("button", { name: "Activar tema oscuro" }).click()
  await expect(thumb).toHaveCSS("background-color", "rgb(10, 10, 10)")
  await expect(thumb).toHaveCSS("border-top-color", "rgb(250, 250, 250)")
})

test("rendered views have no runtime errors", async ({ page }) => {
  const screenshots = process.env.DESKTOP_SCREENSHOTS
  const messages: string[] = []
  page.on("pageerror", error => messages.push(error.message))
  page.on("console", message => {
    if (message.type() === "error" || message.type() === "warning") messages.push(message.text())
  })
  if (screenshots) await mkdir(screenshots, { recursive: true })
  for (const theme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" })
    for (const view of ["chat", "dashboard"] as const) {
      await page.goto(`/#${view}`)
      await expect(page).toHaveTitle("Pizarra · Design Skills Router")
      await expect(page.getByRole("heading", { name: view === "chat" ? "Diseño de la pizarra" : "Resumen del espacio" })).toBeVisible()
      const root = page.locator("html")
      if ((await root.evaluate(el => el.classList.contains("dark"))) !== (theme === "dark")) {
        await page.getByRole("button", { name: theme === "dark" ? "Activar tema oscuro" : "Activar tema claro" }).click()
      }
      if (theme === "dark") await expect(root).toHaveClass(/dark/)
      else await expect(root).not.toHaveClass(/dark/)
      if (view === "dashboard") await expect(page.locator(".recharts-surface").first()).toBeVisible()
      await expect.poll(() => page.evaluate(async () => {
        await document.fonts.ready
        return [...document.fonts].filter(font => font.status === "loaded").length
      })).toBeGreaterThanOrEqual(2)
      await expect(page.locator("vite-error-overlay")).toHaveCount(0)
      if (screenshots) {
        await page.screenshot({ path: join(screenshots, `${view}-${theme}.png`), animations: "disabled" })
      }
    }
  }
  expect(messages).toEqual([])
})

test("the agent inspector tabs fill their segmented list edge to edge", async ({ page }) => {
  await page.goto("/#map")
  await page.getByRole("button", { name: "Agente UI" }).click()
  const list = page.getByRole("tablist", { name: "Modos del inspector" })
  await expect(list.getByRole("tab", { name: "Flujos" })).toHaveAttribute("aria-selected", "true")
  const edges = await list.evaluate(element => {
    const box = element.getBoundingClientRect()
    const tabs = [...element.querySelectorAll('[role="tab"]')].map(tab => tab.getBoundingClientRect())
    const border = parseFloat(getComputedStyle(element).borderLeftWidth)
    return {
      start: Math.abs(Math.round(tabs[0].left - box.left - border)),
      end: Math.abs(Math.round(box.right - border - tabs[tabs.length - 1].right)),
    }
  })
  expect(edges).toEqual({ start: 0, end: 0 })
})
