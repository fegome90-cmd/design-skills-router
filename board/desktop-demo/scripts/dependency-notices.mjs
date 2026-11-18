import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs"

const root = new URL("../", import.meta.url)
const lock = JSON.parse(readFileSync(new URL("package-lock.json", root), "utf8"))
const notices = []

for (const [path, entry] of Object.entries(lock.packages)) {
  if (!path || entry.dev) continue
  const directory = new URL(path + "/", root)
  const manifest = new URL("package.json", directory)
  if (!existsSync(manifest)) continue
  const { name, version, license } = JSON.parse(readFileSync(manifest, "utf8"))
  const files = readdirSync(directory, { withFileTypes: true })
    .filter(file => file.isFile() && /^(?:LICENSE|LICENCE|COPYING|NOTICE)(?:[._-]|$)/i.test(file.name))
    .map(file => file.name)
    .sort()

  if (!license || !files.length) {
    throw new Error(`Missing license metadata or notice for ${name}@${version}`)
  }
  const contents = files.map(file => `${file}\n\n${readFileSync(new URL(file, directory), "utf8").trim()}`)
  notices.push(`${name}@${version} · ${license}\n\n${contents.join("\n\n")}`)
}

const output = new URL("dist/licenses/", root)
mkdirSync(output, { recursive: true })
writeFileSync(new URL("dependencies.txt", output), notices.join("\n\n----------------------------------------\n\n") + "\n")
console.log(`Included license notices for ${notices.length} installed production dependencies.`)
