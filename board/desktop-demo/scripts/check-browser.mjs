import { execFile } from "node:child_process"
import { mkdtemp, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import { basename, join } from "node:path"
import { fileURLToPath } from "node:url"
import { promisify } from "node:util"
import { createServer } from "vite"

const runFile = promisify(execFile)
const project = fileURLToPath(new URL("../", import.meta.url))
const cli = fileURLToPath(new URL("../node_modules/@playwright/cli/playwright-cli.js", import.meta.url))
const workspace = await mkdtemp(join(tmpdir(), "desktop-demo-smoke-"))
const session = basename(workspace)

async function runCli(...args) {
  const { stdout } = await runFile(process.execPath, [cli, "--json", `-s=${session}`, ...args], {
    cwd: workspace,
    timeout: 30_000,
  })
  const reply = JSON.parse(stdout)
  if (reply.isError) throw new Error(reply.error)
  return reply
}

const checkDashboard = `async (page) => {
  await page.getByRole("heading", { name: "Resumen del espacio" }).waitFor({ timeout: 8000 });
  await page.getByRole("button", { name: "7 días", exact: true }).click({ timeout: 8000 });
  await page.getByRole("heading", { name: "Actividad semanal" }).waitFor({ timeout: 8000 });
  return "desktop-dashboard-ready";
}`

let server
try {
  server = await createServer({
    root: project,
    cacheDir: join(workspace, "vite"),
    logLevel: "error",
    server: { host: "127.0.0.1", port: 0, strictPort: true },
  })
  await server.listen()
  const { port } = server.httpServer.address()
  await runCli("open", `http://127.0.0.1:${port}/#dashboard`, "--browser=chromium", "--idle-timeout=20000")
  const reply = await runCli("run-code", checkDashboard)
  if (reply.result !== JSON.stringify("desktop-dashboard-ready")) {
    throw new Error("The dashboard smoke check did not report success.")
  }
  console.log("Playwright CLI: opened the dashboard and switched to the weekly period.")
} finally {
  try {
    await runCli("close")
  } finally {
    try {
      await server?.close()
    } finally {
      await rm(workspace, { recursive: true, force: true })
    }
  }
}
