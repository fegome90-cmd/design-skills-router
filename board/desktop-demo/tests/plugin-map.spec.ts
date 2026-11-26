import { expect, test, type Browser, type Locator, type Page } from "@playwright/test"
import type { Core } from "cytoscape"
import { copyFileSync, existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs"
import { readFile } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"

type GraphEdge = { from: string; to: string; kind: string; condition: string }
type GraphNode = { id: string; title: string; group: string; path: string }
const graphPath = fileURLToPath(new URL("../../../release/design-router-mapa-fuentes.json", import.meta.url))
const graph = JSON.parse(readFileSync(graphPath, "utf8")) as { root: string; nodes: GraphNode[]; edges: GraphEdge[] }
const sourceNode = graph.nodes.find(node => node.id === "py-runner-show-node")!
const rootNode = graph.nodes.find(node => node.id === graph.root)!
const graphNodes = new Map(graph.nodes.map(node => [node.id, node]))
const standaloneFile = fileURLToPath(new URL("../dist/standalone/design-router-desktop.html", import.meta.url))

type Target = "web" | "standalone"

/**
 * Opens the map on a node. The standalone target loads the single HTML file
 * from file:// with the network switched off and fails on any outside request.
 */
async function openMap(browser: Browser, target: Target, width: number, baseURL: string, file = standaloneFile, hasTouch = false) {
  if (target === "standalone") {
    expect(existsSync(file), "Run `npm run build:standalone` first").toBe(true)
  }
  const context = await browser.newContext({
    acceptDownloads: true,
    hasTouch,
    offline: target === "standalone",
    viewport: { width, height: 900 },
  })
  const outside: string[] = []
  const errors: string[] = []
  const origin = new URL(baseURL).origin
  await context.route(/^https?:\/\//, route => {
    if (target === "web" && new URL(route.request().url()).origin === origin) return route.continue()
    outside.push(route.request().url())
    return route.abort()
  })
  const page = await context.newPage()
  page.on("pageerror", error => errors.push(error.message))
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()) })
  const start = target === "standalone" ? pathToFileURL(file).href : new URL("/", baseURL).href
  try {
    await page.goto(`${start}#router-node-${sourceNode.id}`)
  } catch (error) {
    await context.close()
    throw error
  }
  return {
    page,
    async close() {
      try {
        expect(outside, "requests outside the page").toEqual([])
        expect(errors, "runtime errors").toEqual([])
      } finally {
        await context.close()
      }
    },
  }
}

const heading = (page: Page, node: GraphNode) => page.getByRole("heading", { level: 1, name: node.title, exact: true })

async function relationDestination(link: Locator) {
  const href = await link.getAttribute("href")
  return graphNodes.get(decodeURIComponent(href!.replace(/^#router-node-/, "")))!
}

const flowCanvas = (page: Page) => page.getByRole("img", { name: /^Flujo de relaciones de / })

async function readFlow(locator: Locator, title: string) {
  await expect(locator).toHaveAttribute("data-ready", "true")
  const read = () => locator.evaluate(element => {
    const cy = (element as HTMLElement & { _cyreg?: { cy?: Core } })._cyreg?.cy
    if (!cy) return null

    const probe = document.createElement("canvas").getContext("2d", { willReadFrequently: true })!
    const rgb = (colour: string) => {
      probe.clearRect(0, 0, 1, 1)
      probe.fillStyle = colour
      probe.fillRect(0, 0, 1, 1)
      return Array.from(probe.getImageData(0, 0, 1, 1).data).slice(0, 3)
    }
    const decorations = { includeOverlays: false, includeUnderlays: false }
    const labelOnly = { ...decorations, includeNodes: false, includeEdges: false, includeLabels: true }
    const focus = cy.$id("focus")
    return {
      title: focus.style("label").replaceAll("\u200b", ""),
      zoom: cy.zoom(),
      width: cy.width(),
      height: cy.height(),
      centre: focus.renderedPosition(),
      background: rgb(getComputedStyle(element).backgroundColor),
      nodes: cy.nodes().map(node => ({
        id: node.id(),
        x: node.position("x"),
        point: node.renderedPosition(),
        target: node.data("target") as string | undefined,
        side: node.data("side") as "in" | "out" | undefined,
        bundle: node.hasClass("bundle"),
        keyboardFocus: node.hasClass("kbd-focus"),
        borderWidth: parseFloat(node.style("border-width")),
        underlay: rgb(node.style("underlay-color")),
        underlayOpacity: parseFloat(node.style("underlay-opacity")),
        underlayPadding: parseFloat(node.style("underlay-padding")),
        rendered: node.renderedBoundingBox({ includeLabels: false }),
        font: parseFloat(node.style("font-size")),
        wrap: node.style("text-wrap"),
        text: node.style("label"),
        // Cytoscape exposes the actual wrapped canvas lines only in its renderer cache.
        lines: (node as typeof node & {
          _private: { rscratch: { labelWrapCachedLines?: string[] } }
        })._private.rscratch.labelWrapCachedLines ?? [],
        body: node.boundingBox({ ...decorations, includeLabels: false }),
        label: node.boundingBox(labelOnly),
        border: rgb(node.style("border-color")),
        fill: rgb(node.style("background-color")),
      })),
      edges: cy.edges().map(edge => ({
        id: edge.id(),
        labels: [edge.style("label"), edge.style("source-label"), edge.style("target-label")],
        arrowShape: edge.style("target-arrow-shape"),
        arrow: rgb(edge.style("target-arrow-color")),
      })),
    }
  })
  await expect.poll(async () => {
    const flow = await read()
    return flow && { title: flow.title, drawn: flow.nodes.length > 1 && flow.edges.length > 0 }
  }).toEqual({ title, drawn: true })
  return (await read())!
}

function contrast(left: number[], right: number[]) {
  const luminance = (rgb: number[]) => rgb.reduce((sum, value, index) => {
    const srgb = value / 255
    return sum + [0.2126, 0.7152, 0.0722][index] * (srgb <= 0.04045 ? srgb / 12.92 : ((srgb + 0.055) / 1.055) ** 2.4)
  }, 0)
  const a = luminance(left) + 0.05
  const b = luminance(right) + 0.05
  return Math.max(a, b) / Math.min(a, b)
}

function expectLegible(flow: Awaited<ReturnType<typeof readFlow>>) {
  expect(flow.zoom).toBe(1)
  expect(flow.centre.x).toBeCloseTo(flow.width / 2)
  expect(flow.centre.y).toBeCloseTo(flow.height / 2)

  for (const node of flow.nodes) {
    const { body, label, id } = node
    expect(node.font, id).toBe(node.bundle ? 12 : 13)
    expect(node.wrap, id).toBe("wrap")
    expect(label.w, id).toBeGreaterThan(0)
    expect(label.h, id).toBeGreaterThan(0)
    expect(label.x1, id).toBeGreaterThanOrEqual(body.x1)
    expect(label.x2, id).toBeLessThanOrEqual(body.x2)
    expect(label.y1, id).toBeGreaterThanOrEqual(body.y1)
    expect(label.y2, id).toBeLessThanOrEqual(body.y2)
    expect(contrast(node.border, flow.background), id).toBeGreaterThanOrEqual(3)
    if (id !== "focus") expect(contrast(node.border, node.fill), id).toBeGreaterThanOrEqual(3)
  }

  for (const x of new Set(flow.nodes.map(node => node.x))) {
    const column = flow.nodes.filter(node => node.x === x).sort((a, b) => a.body.y1 - b.body.y1)
    for (let i = 1; i < column.length; i++) {
      expect(column[i].body.y1, column[i].id).toBeGreaterThanOrEqual(column[i - 1].body.y2)
    }
  }

  for (const edge of flow.edges) {
    expect(edge.arrowShape, edge.id).toBe("triangle")
    expect(contrast(edge.arrow, flow.background), edge.id).toBeGreaterThanOrEqual(3)
  }
}

async function clickFlowNode(canvas: Locator, id: string, title: string) {
  const node = (await readFlow(canvas, title)).nodes.find(node => node.id === id)!
  const point = await canvas.evaluate((element, position) => {
    const rect = element.getBoundingClientRect()
    return { x: rect.left + element.clientLeft + position.x, y: rect.top + element.clientTop + position.y }
  }, node.point)
  expect(await canvas.evaluate((element, { x, y }) => element.contains(document.elementFromPoint(x, y)), point),
    `Cytoscape node ${id} is inside the viewport and not covered`).toBe(true)
  await canvas.page().mouse.click(point.x, point.y)
}

for (const target of ["web", "standalone"] as const) {
  test.describe(`plugin map · ${target}`, () => {
    test("searches, filters, follows links and keeps history on desktop", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      const rail = page.getByRole("navigation", { name: "Navegación principal" })
      const index = page.getByRole("navigation", { name: "Nodos del plugin" })

      await expect(heading(page, sourceNode)).toBeVisible()
      await expect(rail.getByRole("link", { name: "Mapa del plugin" })).toHaveAttribute("aria-current", "page")
      await expect(page.getByRole("complementary", { name: "Panel contextual" })
        .getByRole("heading", { name: "Nodos del plugin" })).toBeVisible()
      await expect(index.getByRole("status")).toHaveText(`${graph.nodes.length} nodos`)

      await index.locator(`a[href="#router-node-${rootNode.id}"]`).click()
      await expect(heading(page, rootNode)).toBeFocused()
      await page.goBack()
      await expect(heading(page, sourceNode)).toBeVisible()
      await page.goForward()
      await expect(heading(page, rootNode)).toBeVisible()
      await page.goBack()

      await page.getByRole("button", { name: "Ver fuente" }).click()
      await expect(page.locator(".node-source pre")).toBeVisible()

      const relation = page.getByRole("list", { name: "Conduce a", exact: true }).getByRole("link").first()
      const related = await relationDestination(relation)
      await relation.click()
      await expect(heading(page, related)).toBeFocused()

      await index.getByRole("searchbox", { name: "Buscar nodos" }).fill("Router.packet")
      await expect(index.locator(`a[href="#router-node-${sourceNode.id}"]`)).toBeVisible()
      await expect(index.locator(`a[href="#router-node-${rootNode.id}"]`)).toHaveCount(0)
      await index.getByRole("combobox", { name: "Grupo" }).click()
      await page.getByRole("option", { name: sourceNode.group, exact: true }).click()
      await expect(index.locator(`a[href="#router-node-${sourceNode.id}"]`)).toBeVisible()

      await rail.getByRole("link", { name: "Chat" }).click()
      await rail.getByRole("link", { name: "Mapa del plugin" }).click()
      await expect(index.getByRole("searchbox", { name: "Buscar nodos" })).toHaveValue("Router.packet")
      await expect(heading(page, related)).toBeVisible()

      for (const font of ['400 16px "Geist"', '400 14px "Geist Mono"']) {
        expect(await page.evaluate(async family =>
          (await document.fonts.load(family, "áñ")).some(face => face.status === "loaded"), font)).toBe(true)
      }

      const download = page.waitForEvent("download")
      await page.getByRole("button", { name: "Exportar mapa" }).click()
      const file = await download
      expect(file.suggestedFilename()).toBe("design-router-mapa-fuentes.json")
      expect(JSON.parse(await readFile((await file.path())!, "utf8"))).toEqual(graph)
      await close()
    })

    test("relations are split by direction and fold above 14", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      const outgoing = page.getByRole("list", { name: "Conduce a", exact: true })
      const incoming = page.getByRole("list", { name: "Llega desde", exact: true })
      const fold = page.getByRole("button", { name: "Llega desde · 212", exact: true })
      await expect(outgoing.getByRole("link")).toHaveCount(7)
      await expect(fold).toHaveAttribute("aria-expanded", "false")
      await expect(page.locator(".node-relations[aria-label='Llega desde']")).toHaveCount(0)

      await fold.focus()
      await page.keyboard.press("Enter")
      await expect(fold).toHaveAttribute("aria-expanded", "true")
      await expect(incoming.getByRole("link")).toHaveCount(212)
      await page.keyboard.press("Tab")
      await expect(incoming.getByRole("link").first()).toBeFocused()
      await page.keyboard.press("Shift+Tab")
      await expect(fold).toBeFocused()
      await page.keyboard.press("Space")
      await expect(fold).toHaveAttribute("aria-expanded", "false")
      await expect(page.locator(".node-relations[aria-label='Llega desde']")).toHaveCount(0)

      await page.goto(page.url().replace(/#.*$/, "#router-node-rule-layout.local"))
      await expect(incoming.getByRole("link")).toHaveCount(14)
      await expect(page.getByRole("button", { name: "Llega desde · 14", exact: true })).toHaveCount(0)
      await page.goto(page.url().replace(/#.*$/, "#router-node-rule-layout"))
      await expect(page.getByRole("button", { name: "Llega desde · 15", exact: true })).toHaveAttribute("aria-expanded", "false")
      await close()
    })

    test("folds start closed again after navigating to another node and back", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      const fold = page.getByRole("button", { name: "Llega desde · 212", exact: true })
      await fold.click()
      await expect(fold).toHaveAttribute("aria-expanded", "true")
      const link = page.getByRole("list", { name: "Conduce a", exact: true }).getByRole("link").first()
      const related = await relationDestination(link)
      await link.click()
      await expect(heading(page, related)).toBeVisible()
      await page.goBack()
      await expect(heading(page, sourceNode)).toBeVisible()
      await expect(fold).toHaveAttribute("aria-expanded", "false")
      await close()
    })

    test("Q00 keeps directed links and conditions in JSON order and lists Python first", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      await page.goto(page.url().replace(/#.*$/, "#router-node-Q00"))
      const sections = [
        { name: "Consultado desde código Python", idOf: (edge: GraphEdge) => edge.to === "Q00" ? edge.from : null, python: true, count: 2 },
        { name: "Conduce a", idOf: (edge: GraphEdge) => edge.from === "Q00" ? edge.to : null, python: false, count: 5 },
        { name: "Llega desde", idOf: (edge: GraphEdge) => edge.to === "Q00" ? edge.from : null, python: false, count: 3 },
      ]
      await expect(page.locator(".relation-section h3")).toHaveText(sections.map(section => section.name))
      for (const { name, idOf, python, count } of sections) {
        const expected = graph.edges.flatMap(edge => {
          const id = idOf(edge)
          if (!id) return []
          const { path, title } = graphNodes.get(id)!
          if (/\.py$/i.test(path) !== python) return []
          return [{ href: `#router-node-${encodeURIComponent(id)}`, text: title && title !== id ? `${title} · ${id}` : id, condition: edge.condition || null }]
        })
        const rows = page.getByRole("list", { name, exact: true }).getByRole("listitem")
        await expect(rows).toHaveCount(count)
        expect(await rows.evaluateAll(items => items.map(item => ({
          href: item.querySelector("a")?.getAttribute("href"),
          text: item.querySelector("a")?.textContent,
          condition: item.querySelector("p")?.textContent ?? null,
        })))).toEqual(expected)
      }
      await close()
    })

    test("every section of the workspace renders", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      const rail = page.getByRole("navigation", { name: "Navegación principal" })
      const sections = [
        ["Chat", "Conversaciones"],
        ["Dashboard", "Analítica"],
        ["Proyectos", "Proyectos"],
        ["Biblioteca", "Biblioteca"],
        ["Mapa del plugin", "Nodos del plugin"],
        ["Configuración", "Configuración"],
      ]
      for (const [link, contextual] of sections) {
        await rail.getByRole("link", { name: link, exact: true }).click()
        await expect(rail.getByRole("link", { name: link, exact: true })).toHaveAttribute("aria-current", "page")
        await expect(page.getByRole("complementary", { name: "Panel contextual" })
          .getByRole("heading", { level: 2, name: contextual, exact: true })).toBeVisible()
      }
      await page.getByRole("link", { name: "Dashboard", exact: true }).click()
      await expect(page.locator(".activity-chart")).toBeVisible()
      await close()
    })

    test("the node flow follows the Relations card", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      try {
        await expect(page.locator(".plugin-map .detail-card h2")).toHaveText([
          "Ubicación en el código", "Relaciones", "Flujo del nodo",
        ])
      } finally {
        await close()
      }
    })

    test("the node flow has legible Spanish labels and draws the hub at zoom 1", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      try {
        const canvas = flowCanvas(page)
        await expect(canvas).toHaveAttribute("aria-label", /Entradas: 212 relaciones con 212 nodos, agrupadas por tipo y grupo\./)
        const light = await readFlow(canvas, sourceNode.title)
        expect(light.nodes.filter(node => node.bundle).length).toBeGreaterThan(0)
        expect(light.nodes.filter(node => node.target)).toHaveLength(7)
        expectLegible(light)

        const lifetime = await canvas.evaluateHandle(element =>
          (element as HTMLElement & { _cyreg: { cy: Core } })._cyreg.cy)
        await page.getByRole("button", { name: "Activar tema oscuro" }).click()
        const focusFill = (flow: typeof light) => flow.nodes.find(node => node.id === "focus")!.fill
        await expect.poll(async () => focusFill(await readFlow(canvas, sourceNode.title))).not.toEqual(focusFill(light))
        expectLegible(await readFlow(canvas, sourceNode.title))
        expect(await canvas.evaluate((element, before) =>
          (element as HTMLElement & { _cyreg: { cy: Core } })._cyreg.cy === before, lifetime)).toBe(true)
        await lifetime.dispose()
      } finally {
        await close()
      }
    })

    test("the node flow wraps rendered labels only at word boundaries", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      try {
        const flow = await readFlow(flowCanvas(page), sourceNode.title)
        expect(flow.nodes.some(node => node.lines.length > 1)).toBe(true)
        for (const node of flow.nodes) {
          const text = node.text.replaceAll("\u200b", "")
          let offset = 0
          for (const wrapped of node.lines) {
            const line = wrapped.replaceAll("\u200b", "")
            expect(text.slice(offset, offset + line.length), node.id).toBe(line)
            offset += line.length
            const atBoundary = offset === text.length || /[\s._/-]/u.test(text[offset - 1] ?? "")
              || /\s/u.test(text[offset] ?? "")
            expect(atBoundary, `${node.id}: ${JSON.stringify(line)} cuts ${JSON.stringify(text)} at ${offset}`).toBe(true)
            if (text[offset] === "\n") offset++
          }
          expect(offset, node.id).toBe(text.length)
        }
      } finally {
        await close()
      }
    })

    test("the node flow puts translated relation types inside boxes, not on arrows", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      try {
        const canvas = flowCanvas(page)
        await page.goto(page.url().replace(/#.*$/, "#router-node-CAT00"))
        const cat = await readFlow(canvas, graphNodes.get("CAT00")!.title)
        for (const edge of cat.edges) expect.soft(edge.labels, edge.id).toEqual(["", "", ""])
        const neighbour = cat.nodes.find(node => node.target === "R01")!
        expect(neighbour.text.replaceAll("\u200b", "")).toBe(`${graphNodes.get("R01")!.title}\nAlternativa`)
        expect(cat.nodes.map(node => node.text.replaceAll("\u200b", "")).join(" | "))
          .not.toMatch(/\b(alternative|all_branch|template_ref|requires)\b/)
        expectLegible(cat)
        const translated = graph.edges.find(edge => edge.from === "CAT00" && edge.kind === "alternative")!
        await expect(page.getByRole("list", { name: "Conduce a", exact: true }).getByText(translated.condition, { exact: true })).toBeVisible()

        await page.goto(page.url().replace(/#.*$/, "#router-node-ctx-contracts-json"))
        const contracts = await readFlow(canvas, graphNodes.get("ctx-contracts-json")!.title)
        const related = graphNodes.get("py-contracts-evaluate")!
        expect(contracts.nodes.find(node => node.target === related.id)?.text.replaceAll("\u200b", ""))
          .toBe(`${related.title}\nrelación documentada · trazabilidad`)
      } finally {
        await close()
      }
    })

    test("the node flow opens a neighbour through the hash and restores history", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      try {
        const canvas = flowCanvas(page)
        const { nodes } = await readFlow(canvas, sourceNode.title)
        const neighbour = nodes.find(node => node.id.startsWith("out:") && node.target)!
        await canvas.scrollIntoViewIfNeeded()
        await clickFlowNode(canvas, neighbour.id, sourceNode.title)
        await expect.poll(() => new URL(page.url()).hash).toBe(`#router-node-${neighbour.target}`)
        await expect(heading(page, graphNodes.get(neighbour.target!)!)).toBeFocused()
        await page.goBack()
        await expect(heading(page, sourceNode)).toBeVisible()
      } finally {
        await close()
      }
    })

    for (const [nodeId, count] of [[sourceNode.id, 212], ["rule-layout.local", 14]] as const) {
      test(`tapping an incoming bundle focuses its directed relations (${nodeId})`, async ({ browser, baseURL }) => {
        const { page, close } = await openMap(browser, target, 1440, baseURL!)
        try {
          if (nodeId !== sourceNode.id) await page.goto(page.url().replace(/#.*$/, `#router-node-${nodeId}`))
          const title = graphNodes.get(nodeId)!.title
          const canvas = flowCanvas(page)
          const list = page.getByRole("list", { name: "Llega desde", exact: true })
          const fold = page.getByRole("button", { name: `Llega desde · ${count}`, exact: true })
          if (count === 212) await expect(fold).toHaveAttribute("aria-expanded", "false")
          else await expect(fold).toHaveCount(0)

          const bundle = (await readFlow(canvas, title)).nodes.find(node => node.bundle && node.side === "in")!
          await canvas.scrollIntoViewIfNeeded()
          await clickFlowNode(canvas, bundle.id, title)
          if (count === 212) {
            await expect(fold).toHaveAttribute("aria-expanded", "true")
            await expect(fold).toBeFocused()
          } else {
            await expect(list).toBeFocused()
            await expect(list).toHaveAttribute("tabindex", "-1")
          }
          await expect(list.getByRole("link")).toHaveCount(count)
          await expect.poll(() => new URL(page.url()).hash).toBe(`#router-node-${nodeId}`)
        } finally {
          await close()
        }
      })
    }

    test("the flow opens full screen at every width and returns focus to its trigger", async ({ browser, baseURL }) => {
      for (const width of [1440, 390]) {
        const { page, close } = await openMap(browser, target, width, baseURL!)
        try {
          const trigger = page.getByRole("button", { name: "Pantalla completa", exact: true })
          await trigger.click({ timeout: 2500 })
          const dialog = page.getByRole("dialog", { name: `Flujo de ${sourceNode.title}`, exact: true })
          await expect(dialog).toBeVisible()
          const box = (await dialog.boundingBox())!
          expect(box).toEqual({ x: 0, y: 0, width, height: 900 })
          const flow = await readFlow(dialog.locator(".node-flow-canvas"), sourceNode.title)
          expect(flow.zoom).toBe(1)
          expect(flow.centre.x).toBeCloseTo(flow.width / 2)
          expect(flow.centre.y).toBeCloseTo(flow.height / 2)
          await page.keyboard.press("Escape")
          await expect(dialog).toHaveCount(0)
          await expect(trigger).toBeFocused()
        } finally {
          await close()
        }
      }
    })

    test("full-screen zoom responds to all controls within 0.5–3", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      try {
        await page.getByRole("button", { name: "Pantalla completa", exact: true }).click()
        const dialog = page.getByRole("dialog")
        const canvas = dialog.locator(".node-flow-canvas")
        const before = await readFlow(canvas, sourceNode.title)
        const toolbar = dialog.getByRole("toolbar", { name: "Zoom del flujo" })
        const control = (name: string) => toolbar.getByRole("button", { name, exact: true })
        const zoom = async () => (await readFlow(canvas, sourceNode.title)).zoom

        await control("Acercar").click({ timeout: 2500 })
        expect(await zoom()).toBeCloseTo(1.25)
        await control("Alejar").click()
        expect(await zoom()).toBeCloseTo(1)
        await control("Ajustar").click()
        const fitted = await readFlow(canvas, sourceNode.title)
        expect(fitted.zoom).not.toBe(1)
        for (const { body } of fitted.nodes) {
          expect(body.x1 * fitted.zoom + fitted.centre.x).toBeGreaterThanOrEqual(19)
          expect(body.y1 * fitted.zoom + fitted.centre.y).toBeGreaterThanOrEqual(19)
          expect(body.x2 * fitted.zoom + fitted.centre.x).toBeLessThanOrEqual(fitted.width - 19)
          expect(body.y2 * fitted.zoom + fitted.centre.y).toBeLessThanOrEqual(fitted.height - 19)
        }
        await control("Restablecer").click()
        expect(await zoom()).toBe(1)

        await canvas.focus()
        for (let index = 0; index < 10; index++) await page.keyboard.press("-")
        expect(await zoom()).toBe(0.5)
        for (let index = 0; index < 10; index++) await page.keyboard.press("+")
        expect(await zoom()).toBe(3)
        await page.keyboard.press("0")
        expect(await zoom()).toBe(1)
        await page.keyboard.press("Shift+ArrowLeft")
        await page.keyboard.press("Shift+ArrowUp")
        const panned = await readFlow(canvas, sourceNode.title)
        expect(panned.centre).toEqual({ x: before.centre.x + 80, y: before.centre.y + 80 })

        const box = (await canvas.boundingBox())!
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
        await page.mouse.wheel(0, -400)
        await expect.poll(zoom).toBeGreaterThan(1)
        await page.keyboard.press("0")
        expect((await readFlow(canvas, sourceNode.title)).centre).toEqual(before.centre)
      } finally {
        await close()
      }
    })

    for (const width of [320, 390]) {
      test(`full-screen controls and canvas remain usable at ${width} px with touch`, async ({ browser, baseURL }) => {
        const { page, close } = await openMap(browser, target, width, baseURL!, standaloneFile, true)
        try {
          await expect(flowCanvas(page)).toHaveCount(0)
          const trigger = page.getByRole("button", { name: "Pantalla completa", exact: true })
          const labelFits = await trigger.evaluate(button => {
            const label = document.createRange()
            label.selectNode(button.lastChild!)
            const text = label.getBoundingClientRect()
            const frame = button.getBoundingClientRect()
            return button.scrollWidth <= button.clientWidth && text.left >= frame.left && text.right <= frame.right
          })
          expect(labelFits, "the trigger contains the full label").toBe(true)
          await trigger.tap()
          const dialog = page.getByRole("dialog")
          const canvas = dialog.locator(".node-flow-canvas")
          const flow = await readFlow(canvas, sourceNode.title)
          expect(flow.zoom).toBe(1)
          expect(flow.height).toBeGreaterThan(450)
          expect(await dialog.evaluate(el => el.scrollWidth)).toBe(width)
          expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width)
          const toolbar = dialog.getByRole("toolbar", { name: "Zoom del flujo" })
          for (const name of ["Acercar", "Alejar", "Ajustar", "Restablecer"]) {
            await expect(toolbar.getByRole("button", { name, exact: true })).toBeInViewport({ ratio: 1 })
          }
          await toolbar.getByRole("button", { name: "Acercar" }).tap({ timeout: 2500 })
          expect((await readFlow(canvas, sourceNode.title)).zoom).toBe(1.25)
          await dialog.getByRole("button", { name: "Cerrar pantalla completa" }).tap({ timeout: 2500 })
          await expect(dialog).toHaveCount(0)
        } finally {
          await close()
        }
      })
    }

    test("the full-screen header leaves room for the canvas at 200% text size", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 320, baseURL!, standaloneFile, true)
      try {
        const node = graphNodes.get("ADOPT_COST")!
        await page.goto(page.url().replace(/#.*$/, `#router-node-${node.id}`))
        await page.setViewportSize({ width: 320, height: 450 })
        await page.getByRole("button", { name: "Pantalla completa", exact: true }).tap()
        const dialog = page.getByRole("dialog", { name: `Flujo de ${node.title}`, exact: true })
        const canvas = dialog.locator(".node-flow-canvas")
        await readFlow(canvas, node.title)
        await page.evaluate(() => { document.documentElement.style.fontSize = "200%" })
        const toolbar = dialog.getByRole("toolbar", { name: "Zoom del flujo" })
        const dismiss = dialog.getByRole("button", { name: "Cerrar pantalla completa", exact: true })
        await expect.poll(async () => (await canvas.boundingBox())?.height ?? 0).toBeGreaterThan(200)
        await expect(canvas).toBeInViewport({ ratio: 1 })
        await expect(toolbar).toBeInViewport({ ratio: 1 })
        await expect(dismiss).toBeInViewport({ ratio: 1 })

        const zoomIn = toolbar.getByRole("button", { name: "Acercar", exact: true })
        await zoomIn.focus()
        await page.keyboard.press("Shift+Tab")
        const titleBlock = dialog.getByRole("region", { name: "Título y resumen del flujo", exact: true })
        await expect(titleBlock).toBeFocused()
        await page.keyboard.press("End")
        await expect.poll(() => titleBlock.evaluate(el => el.scrollTop)).toBeGreaterThan(0)
        await page.keyboard.press("Tab")
        await expect(zoomIn).toBeFocused()
        await page.keyboard.press("Enter")
        expect((await readFlow(canvas, node.title)).zoom).toBe(1.25)
        await page.keyboard.press("Tab")
        await expect(dismiss).toBeFocused()
        await page.keyboard.press("Enter")
        await expect(dialog).toHaveCount(0)
      } finally {
        await close()
      }
    })

    test("the full-screen hub retains zoom and pan on resize and density redraws", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      try {
        await page.getByRole("button", { name: "Pantalla completa", exact: true }).click()
        const dialog = page.getByRole("dialog")
        const canvas = dialog.locator(".node-flow-canvas")
        const zoom = dialog.getByRole("button", { name: "Acercar", exact: true })
        await readFlow(canvas, sourceNode.title)
        await canvas.focus()
        await page.keyboard.press("+")
        await page.keyboard.press("Shift+ArrowLeft")
        await page.keyboard.press("Shift+ArrowUp")
        const first = await readFlow(canvas, sourceNode.title)
        expect(first.zoom).toBe(1.25)
        expect(first.centre).toEqual({ x: first.width / 2 + 80, y: first.height / 2 + 80 })
        const lifetime = await canvas.evaluateHandle(el => (el as HTMLElement & { _cyreg: { cy: Core } })._cyreg.cy)
        // Hold only the canvas's font reads to observe each redraw in flight.
        const holdDraw = () => page.evaluate(() => {
          const fonts = document.fonts
          const load = fonts.load.bind(fonts)
          let release!: () => void
          const pending = new Promise<void>(resolve => { release = resolve })
          fonts.load = async (...args) => {
            await pending
            return load(...args)
          }
          document.addEventListener("finish-flow-font-read", () => {
            fonts.load = load
            release()
          }, { once: true })
        })
        async function redraw(change: () => Promise<unknown>) {
          await holdDraw()
          await change()
          await expect(canvas).not.toHaveAttribute("data-ready", "true")
          await expect(zoom).toBeDisabled()
          await page.evaluate(() => document.dispatchEvent(new Event("finish-flow-font-read")))
          const flow = await readFlow(canvas, sourceNode.title)
          expect(flow.zoom).toBe(first.zoom)
          expect(flow.centre).toEqual(first.centre)
          await expect(zoom).toBeEnabled()
          return flow
        }

        const resized = await redraw(() => page.setViewportSize({ width: 720, height: 640 }))
        expect(resized.width).toBe(720)
        expect(resized.height).toBeLessThan(first.height)
        await redraw(() => page.evaluate(() => { document.documentElement.dataset.density = "compact" }))
        expect(await canvas.evaluate((el, before) =>
          (el as HTMLElement & { _cyreg: { cy: Core } })._cyreg.cy === before, lifetime)).toBe(true)
        await lifetime.dispose()
        await expect(zoom).toBeEnabled()
      } finally {
        await close()
      }
    })

    test("keyboard walks the full-screen nodes, announces them and keeps its focus visible", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      try {
        await page.getByRole("button", { name: "Pantalla completa", exact: true }).click()
        const dialog = page.getByRole("dialog")
        const canvas = dialog.locator(".node-flow-canvas")
        const live = dialog.locator("[aria-live=polite]")
        const finish = dialog.getByRole("button", { name: "Cerrar pantalla completa" })
        const toolbar = dialog.getByRole("toolbar", { name: "Zoom del flujo" })
        const current = () => readFlow(canvas, sourceNode.title)
        await current()
        await finish.focus()
        await page.keyboard.press("Tab")
        await expect(canvas).toBeFocused()
        await expect(live).toContainText(sourceNode.title)
        await expect(live).toContainText("219 relaciones")

        for (const dark of [false, true, false]) {
          await page.evaluate(dark => document.documentElement.classList.toggle("dark", dark), dark)
          await expect.poll(async () => (await current()).background[0] < 128).toBe(dark)
          const flow = await current()
          const focused = flow.nodes.find(node => node.keyboardFocus)!
          expect(focused.id).toBe("focus")
          expect(focused.borderWidth).toBeGreaterThanOrEqual(2)
          expect(focused.underlayOpacity).toBe(1)
          expect(focused.underlayPadding).toBeGreaterThanOrEqual(2)
          expect(contrast(focused.border, focused.fill)).toBeGreaterThanOrEqual(3)
          expect(contrast(focused.underlay, focused.border)).toBeGreaterThanOrEqual(3)
          expect(contrast(focused.underlay, flow.background)).toBeGreaterThanOrEqual(3)
        }

        await page.keyboard.press("Tab")
        await expect(toolbar.getByRole("button", { name: "Acercar" })).toBeFocused()
        expect((await current()).nodes.some(node => node.keyboardFocus)).toBe(false)
        await page.keyboard.press("Shift+Tab")
        await expect(canvas).toBeFocused()
        await page.keyboard.press("ArrowRight")
        const firstOut = (await current()).nodes.find(node => node.keyboardFocus)!
        expect(firstOut.id).toMatch(/^out:/)
        const expectedTitle = graphNodes.get(firstOut.target!)!.title
        await expect(live).toContainText(expectedTitle)
        expect(await live.textContent()).not.toContain("\u200b")

        await page.keyboard.press("ArrowDown")
        const nextOut = (await current()).nodes.find(node => node.keyboardFocus)!
        expect(nextOut.x).toBe(firstOut.x)
        expect(nextOut.point.y).toBeGreaterThan(firstOut.point.y)
        await page.keyboard.press("ArrowUp")
        expect((await current()).nodes.find(node => node.keyboardFocus)?.id).toBe(firstOut.id)
        await page.keyboard.press("ArrowLeft")
        expect((await current()).nodes.find(node => node.keyboardFocus)?.id).toBe("focus")
        await page.keyboard.press("ArrowLeft")
        const bundle = (await current()).nodes.find(node => node.keyboardFocus)!
        expect(bundle.bundle).toBe(true)
        await expect(live).toContainText("grupo, Enter abre su lista")

        for (let i = 0; i < 6; i++) await page.keyboard.press("+")
        for (let i = 0; i < 20; i++) await page.keyboard.press("Shift+ArrowRight")
        const panned = await current()
        expect(panned.nodes.find(node => node.keyboardFocus)?.id).toBe(bundle.id)
        expect(panned.nodes.find(node => node.keyboardFocus)!.rendered.x2).toBeLessThan(0)
        await page.keyboard.press("ArrowRight")
        const after = await current()
        expect(after.nodes.find(node => node.keyboardFocus)?.id).toBe("focus")
        expect(after.centre).toEqual({ x: after.width / 2, y: after.height / 2 })
      } finally {
        await close()
      }
    })

    for (const input of ["keyboard", "pointer"] as const) {
      test(`opening a neighbour by ${input} keeps full screen and returns to the current heading`, async ({ browser, baseURL }) => {
        const { page, close } = await openMap(browser, target, input === "keyboard" ? 390 : 1440, baseURL!)
        try {
          await page.getByRole("button", { name: "Pantalla completa", exact: true }).click()
          const dialog = page.getByRole("dialog")
          const canvas = dialog.locator(".node-flow-canvas")
          const initial = await readFlow(canvas, sourceNode.title)
          const identity = await dialog.elementHandle()
          let destination: GraphNode
          if (input === "keyboard") {
            await canvas.focus()
            await page.keyboard.press("=")
            await page.keyboard.press("ArrowRight")
            const next = (await readFlow(canvas, sourceNode.title)).nodes.find(node => node.keyboardFocus)!
            destination = graphNodes.get(next.target!)!
            await page.keyboard.press("Enter")
          } else {
            const next = initial.nodes.find(node => node.side === "out" && node.target)!
            destination = graphNodes.get(next.target!)!
            await clickFlowNode(canvas, next.id, sourceNode.title)
          }
          await expect.poll(() => new URL(page.url()).hash).toBe(`#router-node-${destination.id}`)
          await expect(dialog.getByRole("heading", { name: `Flujo de ${destination.title}`, exact: true })).toBeVisible()
          const after = await readFlow(canvas, destination.title)
          expect(after.zoom).toBe(1)
          expect(after.centre).toEqual({ x: after.width / 2, y: after.height / 2 })
          expect(await dialog.evaluate((element, before) => element === before, identity)).toBe(true)
          await identity?.dispose()
          await page.goBack()
          await expect(dialog.getByRole("heading", { name: `Flujo de ${sourceNode.title}`, exact: true })).toBeVisible()
          await page.goForward()
          await expect(dialog.getByRole("heading", { name: `Flujo de ${destination.title}`, exact: true })).toBeVisible()
          await page.keyboard.press("Escape")
          await expect(dialog).toHaveCount(0)
          await expect(heading(page, destination)).toBeFocused()
          await expect(heading(page, destination)).toBeInViewport({ ratio: 1 })
        } finally {
          await close()
        }
      })
    }

    for (const [nodeId, count] of [[sourceNode.id, 212], ["rule-layout.local", 14]] as const) {
      test(`a full-screen group opens its ${count} incoming relations and focuses the list target`, async ({ browser, baseURL }) => {
        const { page, close } = await openMap(browser, target, 1440, baseURL!)
        try {
          await page.goto(page.url().replace(/#.*$/, `#router-node-${nodeId}`))
          const node = graphNodes.get(nodeId)!
          await expect(heading(page, node)).toBeVisible()
          await page.getByRole("button", { name: "Pantalla completa", exact: true }).click()
          const dialog = page.getByRole("dialog")
          const canvas = dialog.locator(".node-flow-canvas")
          await readFlow(canvas, node.title)
          await canvas.focus()
          await page.keyboard.press("ArrowLeft")
          expect((await readFlow(canvas, node.title)).nodes.find(item => item.keyboardFocus)?.bundle).toBe(true)
          await page.keyboard.press("Enter")
          await expect(dialog).toHaveCount(0, { timeout: 2500 })
          const list = page.getByRole("list", { name: "Llega desde", exact: true })
          if (count > 14) {
            const trigger = page.getByRole("button", { name: `Llega desde · ${count}`, exact: true })
            await expect(trigger).toHaveAttribute("aria-expanded", "true")
            await expect(trigger).toBeFocused()
            await expect(trigger).toBeInViewport()
          } else {
            await expect(list).toHaveAttribute("tabindex", "-1")
            await expect(list).toBeFocused()
            await expect(list).toBeInViewport()
          }
          await expect(list.getByRole("link")).toHaveCount(count)
          expect(new URL(page.url()).hash).toBe(`#router-node-${nodeId}`)
        } finally {
          await close()
        }
      })
    }

    test("the inline flow leaves the lists available on narrow screens", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 390, baseURL!)
      try {
        await expect(flowCanvas(page)).toHaveCount(0)
        await expect(page.locator(".node-flow")).toHaveCount(0)
        await expect(page.getByRole("list", { name: "Conduce a", exact: true }).getByRole("link")).toHaveCount(7)
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
      } finally {
        await close()
      }
    })

    for (const density of ["comfortable", "compact"] as const) {
      test(`the inline flow crosses 634 px when resizing the sidebar in ${density} density`, async ({ browser, baseURL }) => {
        const { page, close } = await openMap(browser, target, 1038, baseURL!)
        try {
          if (density === "compact") {
            const rail = page.getByRole("navigation", { name: "Navegación principal" })
            await rail.getByRole("link", { name: "Configuración", exact: true }).click()
            await page.getByRole("combobox", { name: "Densidad de la interfaz" }).click()
            await page.getByRole("option", { name: "Compacta", exact: true }).click()
            await page.goto(page.url().replace(/#.*$/, `#router-node-${sourceNode.id}`))
            await expect(page.locator("html")).toHaveAttribute("data-density", "compact")
          }

          const slot = page.locator(".node-flow-slot")
          await expect(slot).toBeAttached()
          const canvas = flowCanvas(page)
          const handle = page.getByRole("separator", { name: "Redimensionar panel contextual" })
          async function resizeTo(width: number) {
            const box = (await handle.boundingBox())!
            const start = box.x + box.width / 2
            const y = box.y + 200
            const current = (await slot.boundingBox())!.width
            await page.mouse.move(start, y)
            await page.mouse.down()
            await page.mouse.move(start + current - width, y, { steps: 4 })
            await page.mouse.up()
            await expect.poll(async () => Math.abs((await slot.boundingBox())!.width - width)).toBeLessThan(1)
          }

          await resizeTo(634.5)
          const first = await readFlow(canvas, sourceNode.title)
          expectLegible(first)
          await resizeTo(633.5)
          await expect(canvas).toHaveCount(0)
          await expect(page.locator(".node-flow")).toHaveCount(0)
          await resizeTo(638)
          expectLegible(await readFlow(canvas, sourceNode.title))
        } finally {
          await close()
        }
      })
    }

    test("the agent flow searches and filters the node index", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 1440, baseURL!)
      const rail = page.getByRole("navigation", { name: "Navegación principal" })
      await rail.getByRole("link", { name: "Chat", exact: true }).click()
      await page.getByRole("button", { name: "Agente UI" }).click()
      await page.getByRole("button", { name: "Buscar un nodo en el mapa" }).click()
      const result = page.locator(".agent-result-card")
      await expect(result).toHaveAttribute("data-ok", "true")
      await expect(result.getByText("Buscar un nodo en el mapa")).toBeVisible()
      await page.getByRole("button", { name: "Cerrar inspector del agente" }).click()

      const index = page.getByRole("navigation", { name: "Nodos del plugin" })
      await expect(rail.getByRole("link", { name: "Mapa del plugin" })).toHaveAttribute("aria-current", "page")
      await expect(index.getByRole("searchbox", { name: "Buscar nodos" })).toHaveValue("Router.packet")
      await expect(index.getByRole("combobox", { name: "Grupo" })).toHaveText(/Código del flujo/)
      await expect(index.locator(`a[href="#router-node-${sourceNode.id}"]`)).toBeVisible()
      await expect(index.locator(`a[href="#router-node-${rootNode.id}"]`)).toHaveCount(0)
      await close()
    })

    for (const [device, width] of [["desktop", 1440], ["phone", 390]] as const) {
      test(`a keyboard relation gives the heading visible focus on ${device}`, async ({ browser, baseURL }) => {
        const { page, close } = await openMap(browser, target, width, baseURL!)
        const toggle = page.getByRole("button", { name: "Mostrar panel contextual" })
        const index = page.getByRole("navigation", { name: "Nodos del plugin" })
        if (device === "phone") {
          await expect(toggle).toHaveAttribute("aria-expanded", "false")
          await expect(index).not.toBeVisible()
        }

        const link = page.getByRole("list", { name: "Conduce a", exact: true }).getByRole("link").first()
        const related = await relationDestination(link)
        await link.focus()
        await page.keyboard.press("Enter")
        const destination = heading(page, related)
        await expect(destination).toBeFocused()
        const focus = await destination.evaluate(el => {
          const style = getComputedStyle(el)
          return { visible: el.matches(":focus-visible"), style: style.outlineStyle, width: parseFloat(style.outlineWidth) }
        })
        expect(focus.visible).toBe(true)
        expect(focus.style).toBe("solid")
        expect(focus.width).toBeGreaterThanOrEqual(2)
        if (device === "phone") {
          await expect(toggle).toHaveAttribute("aria-expanded", "false")
          await expect(index).not.toBeVisible()
        }
        await close()
      })
    }

    test("on a phone the node panel keeps its search and hands focus to the node", async ({ browser, baseURL }) => {
      const { page, close } = await openMap(browser, target, 390, baseURL!)
      const toggle = page.getByRole("button", { name: "Mostrar panel contextual" })
      const index = page.getByRole("navigation", { name: "Nodos del plugin" })

      await expect(heading(page, sourceNode)).toBeVisible()
      await toggle.click()
      await expect(index).toBeVisible()
      await index.getByRole("searchbox", { name: "Buscar nodos" }).fill("Q00")
      await page.keyboard.press("Escape")
      await expect(index).not.toBeVisible()
      await expect(toggle).toBeFocused()

      await toggle.click()
      await expect(index.getByRole("searchbox", { name: "Buscar nodos" })).toHaveValue("Q00")
      await index.locator(`a[href="#router-node-${rootNode.id}"]`).press("Enter")
      await expect(index).not.toBeVisible()
      await expect(heading(page, rootNode)).toBeFocused()
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
      await close()
    })
  })
}

test("the standalone file draws inline and opens full screen alone in an empty folder, offline", async ({ browser, baseURL }) => {
  const dir = mkdtempSync(join(tmpdir(), "router-standalone-"))
  try {
    const file = join(dir, "design-router-desktop.html")
    copyFileSync(standaloneFile, file)
    const { page, close } = await openMap(browser, "standalone", 1440, baseURL!, file)
    try {
      const canvas = flowCanvas(page)
      const first = await readFlow(canvas, sourceNode.title)
      expect(first.zoom).toBe(1)
      await expect(canvas).toBeVisible()
      const fonts = await page.evaluate(() => [...document.fonts].filter(font => font.family === "Geist").map(font => font.status))
      expect(fonts).toContain("loaded")
      const trigger = page.getByRole("button", { name: "Pantalla completa", exact: true })
      await trigger.click()
      const dialog = page.getByRole("dialog")
      expect((await readFlow(dialog.locator(".node-flow-canvas"), sourceNode.title)).zoom).toBe(1)
      await page.keyboard.press("Escape")
      await expect(dialog).toHaveCount(0)
      await expect(trigger).toBeFocused()
    } finally {
      await close()
    }
  } finally {
    rmSync(dir, { recursive: true })
  }
})
