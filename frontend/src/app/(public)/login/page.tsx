import { StatusBadge } from "@/components/shared/StatusBadge";

export default function LoginPage() {
  return (
    <section className="mx-auto max-w-xl">
      <div className="card">
        <h3>Sign in to GrantPilot</h3>
        <p className="mt-2 text-secondary">
          Continue with Google or request a magic link to access your workspace.
        </p>
        <div className="mt-6 space-y-4">
          <button type="button" className="btn-primary w-full">
            Continue with Google
          </button>
          <div className="text-center text-secondary">or</div>
          <div className="space-y-2">
            <label htmlFor="email" className="block text-sm font-medium text-brand-text-primary">
              Work email
            </label>
            <input
              id="email"
              type="email"
              placeholder="you@example.org"
              className="h-11 w-full rounded-[8px] border border-brand-border bg-brand-card-bg px-4 text-[14px] outline-none focus:border-brand-primary"
            />
            <button
              type="button"
              className="h-11 w-full rounded-[8px] border border-brand-primary bg-transparent px-4 text-base font-semibold text-brand-primary"
            >
              Send Magic Link
            </button>
          </div>
        </div>
      </div>
      <div className="mt-4">
        <StatusBadge label="MVP UI stub" tone="neutral" />
      </div>
    </section>
  );
}

