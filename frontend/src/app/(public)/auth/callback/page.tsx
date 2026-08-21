import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";

export default function AuthCallbackPage() {
  return (
    <section className="mx-auto max-w-2xl">
      <LoadingSkeleton lines={2} />
      <p className="mt-4 text-secondary">Signing you in...</p>
    </section>
  );
}

