import { spawnSync } from "node:child_process"
import { relative } from "node:path"
import { fileURLToPath } from "node:url"

const project = fileURLToPath(new URL("../", import.meta.url))
const cli = fileURLToPath(new URL("../node_modules/impeccable/cli/bin/cli.js", import.meta.url))
const result = spawnSync(process.execPath, [cli, "detect", "--json", "src"], {
  cwd: project,
  encoding: "utf8",
  timeout: 30_000,
})

if (result.error) throw result.error
if (result.status !== 0 && result.status !== 2) {
  throw new Error(result.stderr.trim() || `Impeccable exited with status ${result.status}`)
}

const findings = JSON.parse(result.stdout)
if (!Array.isArray(findings)) throw new Error("Impeccable did not return a findings array.")

let errors = 0
for (const { file, line, severity, antipattern, snippet } of findings) {
  const message = `${relative(project, file)}:${line} ${severity} [${antipattern}] ${snippet}`
  if (severity === "error") {
    errors++
    console.error(message)
  } else {
    console.warn(message)
  }
}

console.log(`Impeccable: ${errors} errors, ${findings.length - errors} warnings or advisories.`)
if (errors) process.exitCode = 1
