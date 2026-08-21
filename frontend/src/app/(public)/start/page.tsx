import { ErrorDisplay } from "@/components/shared/ErrorDisplay";

export default function StartPage() {
  return (
    <section className="space-y-6">
      <div className="card">
        <h3>Start Fit Check</h3>
        <p className="mt-2 text-secondary">
          This page receives opportunity context from NGOInfo.org and routes users
          through authentication and profile checks.
        </p>
      </div>
      <ErrorDisplay message="Opportunity context is not connected yet in this UI skeleton." />
    </section>
  );
}

