import { describe, expect, test } from "vitest"
import { flowColumns, stackRows } from "@/node-flow-layout"

describe("node flow layout", () => {
  test("requires 634 useful pixels for three columns at zoom 1", () => {
    expect(flowColumns(633)).toBeNull()
    expect(flowColumns(633.5)).toBeNull()
    expect(flowColumns(634)).toEqual({ nodeWidth: 150, columnGap: 72 })
    expect(flowColumns(1100)).toEqual({ nodeWidth: 220, columnGap: 150 })
  })

  test("stacks rows by their measured heights, centred on zero", () => {
    expect(stackRows([40, 60], 14)).toEqual([-37, 27])
  })
})
