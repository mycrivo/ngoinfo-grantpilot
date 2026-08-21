type StatusTone = "success" | "warning" | "error" | "neutral";

type StatusBadgeProps = {
  label: string;
  tone?: StatusTone;
};

const toneClasses: Record<StatusTone, string> = {
  success: "bg-brand-success/10 text-brand-success border-brand-success/30",
  warning: "bg-brand-warning/10 text-brand-warning border-brand-warning/30",
  error: "bg-brand-error/10 text-brand-error border-brand-error/30",
  neutral: "bg-brand-neutral/10 text-brand-neutral border-brand-neutral/30",
};

export function StatusBadge({ label, tone = "neutral" }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-1 text-sm font-medium ${toneClasses[tone]}`}
    >
      {label}
    </span>
  );
}

