import Link from "next/link";

export default function BillingSuccessPage() {
  return (
    <section className="mx-auto max-w-2xl">
      <div className="card">
        <h3>Subscription activated</h3>
        <p className="mt-2 text-secondary">
          Your plan is active. You can now continue in your dashboard.
        </p>
        <Link href="/dashboard" className="btn-primary mt-6 inline-flex items-center">
          Go to Dashboard
        </Link>
      </div>
    </section>
  );
}

