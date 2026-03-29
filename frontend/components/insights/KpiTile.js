export default function KpiTile({ label, value, hint }) {
	return (
		<article className="card p-4 rise">
			<p className="label">{label}</p>
			<p className="mt-2 text-2xl font-extrabold tracking-tight">{value}</p>
			{hint ? <p className="mt-2 text-sm text-(--text-muted)">{hint}</p> : null}
		</article>
	)
}
