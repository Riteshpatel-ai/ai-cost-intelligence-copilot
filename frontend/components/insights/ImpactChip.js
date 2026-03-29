function formatInr(value) {
	return Intl.NumberFormat('en-IN', {
		style: 'currency',
		currency: 'INR',
		maximumFractionDigits: 0,
	}).format(value || 0)
}

export default function ImpactChip({ amount }) {
	return (
		<span className="pill">
			<span className="h-2 w-2 rounded-full bg-(--brand)" />
			{formatInr(amount)} recoverable impact
		</span>
	)
}
