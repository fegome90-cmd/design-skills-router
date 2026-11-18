import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { App } from "@/app"
import { TooltipProvider } from "@/components/ui/tooltip"
import "./styles.css"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <TooltipProvider delay={250}>
      <App />
    </TooltipProvider>
  </StrictMode>
)
