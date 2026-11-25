import { afterEach, describe, expect, test } from "vitest"
import type { AgentAction } from "@ui-sdk/react/agent"
import { allow, setAgentConfirmHandler } from "@/agent"

const step = (confirm: boolean) => ({ confirm }) as unknown as AgentAction

describe("agent permissions", () => {
  afterEach(() => setAgentConfirmHandler(null))

  test("unmarked steps run without asking", () => {
    expect(allow(step(false))).toBe(true)
  })

  test("confirmed steps are refused when nobody can answer", () => {
    expect(allow(step(true))).toBe(false)
  })

  test("confirmed steps wait for the person's answer", async () => {
    setAgentConfirmHandler(() => Promise.resolve(false))
    await expect(allow(step(true))).resolves.toBe(false)
    setAgentConfirmHandler(() => true)
    expect(allow(step(true))).toBe(true)
  })
})
