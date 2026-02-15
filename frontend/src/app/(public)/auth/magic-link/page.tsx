import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";

export default function MagicLinkPage() {
  return (
    <section className="mx-auto max-w-2xl">
      <LoadingSkeleton lines={2} />
      <p className="mt-4 text-secondary">Validating your magic link...</p>
    </section>
  );
}

