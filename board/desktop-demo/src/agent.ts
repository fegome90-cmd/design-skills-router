import { createAgent, registerTools, type AgentAction } from "@ui-sdk/react/agent"

export type AgentConfirmHandler = (step: AgentAction) => boolean | Promise<boolean>

let confirmHandler: AgentConfirmHandler | null = null

export function setAgentConfirmHandler(handler: AgentConfirmHandler | null) {
  confirmHandler = handler
}

// Steps marked with data-agent-confirm wait for the person, whether they come
// from the in-app drawer or from a browser agent through WebMCP.
export function allow(step: AgentAction) {
  if (!step.confirm) return true
  if (confirmHandler) return confirmHandler(step)
  return false
}

export const agent = createAgent({ allow })

export function registerAppWebMCP() {
  return registerTools(agent, { allow })
}
