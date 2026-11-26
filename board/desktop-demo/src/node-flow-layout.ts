const minNodeWidth = 150
const maxNodeWidth = 220
export const flowPadding = 40

/** Columns for incoming → node → outgoing at zoom 1, or null when they do not fit. */
export function flowColumns(width: number) {
  for (const columnGap of [150, 72]) {
    const nodeWidth = Math.min(maxNodeWidth, Math.floor((width - 2 * columnGap - flowPadding) / 3))
    if (nodeWidth >= minNodeWidth) return { nodeWidth, columnGap }
  }
  return null
}

/** Row centres for a column centred on zero, using the actual height of each row. */
export function stackRows(heights: readonly number[], gap: number) {
  const total = heights.reduce((sum, height) => sum + height, 0) + gap * Math.max(0, heights.length - 1)
  let top = -total / 2
  return heights.map(height => {
    const centre = top + height / 2
    top += height + gap
    return centre
  })
}
