export function advanceSimulationElapsed(
  currentElapsed: number,
  delta: number,
  isPaused: boolean
): number {
  if (isPaused) return currentElapsed
  return currentElapsed + delta
}
