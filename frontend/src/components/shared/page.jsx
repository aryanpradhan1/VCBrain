import { motion } from "motion/react"

// Consistent page entrance: quick fade + 8px rise, iOS-like ease-out.
export function Page({ children, className }) {
  return (
    <motion.main
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className={className}>
      {children}
    </motion.main>
  )
}

// Stagger container + item for lists of cards/rows.
export const stagger = {
  container: {
    animate: { transition: { staggerChildren: 0.05 } },
  },
  item: {
    initial: { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
  },
}
