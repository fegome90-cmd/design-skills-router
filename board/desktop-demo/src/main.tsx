import { registerAppWebMCP } from "./agent"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { App } from "@/app"
import "./styles.css"

const unregister = registerAppWebMCP()
if (import.meta.hot) import.meta.hot.dispose(unregister)

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
