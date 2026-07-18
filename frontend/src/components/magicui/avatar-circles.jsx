// Vendored from Magic UI (magicui.design/r/avatar-circles.json), TSX→JSX.
// Size made a pixel prop (dynamic Tailwind classes don't compile).
import { cn } from "@/lib/utils"

export const AvatarCircles = ({ numPeople, className, avatarUrls, size = 40 }) => {
  const dim = { width: size, height: size }
  return (
    <div className={cn("z-10 flex -space-x-3", className)}>
      {avatarUrls.map((url, index) => (
        <img
          key={index}
          style={dim}
          className="rounded-full border-2 border-white object-cover shadow-sm"
          src={url.imageUrl}
          alt={url.alt ?? `Avatar ${index + 1}`}
          title={url.alt}
          loading="lazy"
        />
      ))}
      {(numPeople ?? 0) > 0 && (
        <span
          style={dim}
          className="flex items-center justify-center rounded-full border-2 border-white bg-slate-900 text-center text-xs font-medium text-white">
          +{numPeople}
        </span>
      )}
    </div>
  )
}
