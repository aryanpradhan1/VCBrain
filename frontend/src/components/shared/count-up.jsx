import { useEffect } from "react"
import { animate, motion, useMotionValue, useTransform } from "motion/react"

// Animated number for score reveals. Renders the exact target when animation ends.
export function CountUp({ value, duration = 1.1, delay = 0, className }) {
  const mv = useMotionValue(0)
  const rounded = useTransform(mv, (v) => Math.round(v))

  useEffect(() => {
    const controls = animate(mv, value, { duration, delay, ease: [0.16, 1, 0.3, 1] })
    return controls.stop
  }, [value, duration, delay, mv])

  return <motion.span className={className}>{rounded}</motion.span>
}
