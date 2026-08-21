type LoadingSkeletonProps = {
  lines?: number;
};

export function LoadingSkeleton({ lines = 3 }: LoadingSkeletonProps) {
  return (
    <div
      className="card animate-pulse space-y-2"
      role="status"
      aria-label="Loading content"
    >
      <div className="h-6 w-1/3 rounded bg-brand-divider" />
      {Array.from({ length: lines }).map((_, index) => (
        <div key={index} className="h-4 w-full rounded bg-brand-divider" />
      ))}
    </div>
  );
}

