export default function InsightCard({ text }) {
  return (
    <div className="rounded-xl border border-(--border) bg-(--surface-soft) p-3 text-sm leading-relaxed flex gap-2.5 items-start">
      <span className="mt-1 h-2 w-2 rounded-full bg-(--brand) shrink-0" />
      <p>{text}</p>
    </div>
  )
}

