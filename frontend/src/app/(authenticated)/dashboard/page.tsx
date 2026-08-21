import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { StatusBadge } from "@/components/shared/StatusBadge";

export default function DashboardPage() {
  return (
    <section className="space-y-6">
      <div className="card">
        <h3>Dashboard</h3>
        <p className="mt-2 text-secondary">
          Quota overview, profile status, recent fit scans, and proposal history will
          render here.
        </p>
        <div className="mt-4 flex gap-2">
          <StatusBadge label="RECOMMENDED" tone="success" />
          <StatusBadge label="APPLY_WITH_CAVEATS" tone="warning" />
          <StatusBadge label="NOT_RECOMMENDED" tone="error" />
        </div>
      </div>
      <LoadingSkeleton lines={4} />
    </section>
  );
}

