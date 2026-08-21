import Link from "next/link";

export default function BillingCancelPage() {
  return (
    <section className="mx-auto max-w-2xl">
      <div className="card">
        <h3>Checkout cancelled</h3>
        <p className="mt-2 text-secondary">
          No changes were made to your subscription. You can upgrade any time.
        </p>
        <Link href="/dashboard" className="btn-primary mt-6 inline-flex items-center">
          Back to Dashboard
        </Link>
      </div>
    </section>
  );
}

