import { useEffect, useState } from "react"
import { nodeHashPrefix } from "@/graph"

const preferencePrefix = "dsr.desktop.v1."

export function readPreference(key: string) {
  try {
    return window.localStorage.getItem(preferencePrefix + key)
  } catch {
    return null
  }
}

export function writePreference(key: string, value: string) {
  try {
    window.localStorage.setItem(preferencePrefix + key, value)
  } catch {
    // The current tab still retains the preference in memory.
  }
}

export const sidebarRange = { minimum: 240, initial: 270, maximum: 320 }

export function readSidebarWidth() {
  const width = Number(readPreference("sidebar-width"))
  return width >= sidebarRange.minimum && width <= sidebarRange.maximum ? width : sidebarRange.initial
}

export function useTheme() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const stored = readPreference("theme")
    return stored === "light" || stored === "dark"
      ? stored
      : window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
  })

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark")
    document.documentElement.style.colorScheme = theme
    writePreference("theme", theme)
  }, [theme])

  return [theme, setTheme] as const
}

export const destinations = ["chat", "dashboard", "projects", "library", "map", "settings"] as const
export type Destination = typeof destinations[number]

function getDestination(): Destination {
  // Node links such as #router-node-Q00 belong to the plugin map.
  if (window.location.hash.startsWith(nodeHashPrefix)) return "map"
  const section = window.location.hash.slice(1)
  return destinations.find(destination => destination === section) ?? "chat"
}

export function useDestination() {
  const [destination, setDestination] = useState(getDestination)
  useEffect(() => {
    const readHash = () => setDestination(getDestination())
    window.addEventListener("hashchange", readHash)
    return () => window.removeEventListener("hashchange", readHash)
  }, [])
  return destination
}
