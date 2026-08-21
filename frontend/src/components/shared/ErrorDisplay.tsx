type ErrorDisplayProps = {
  title?: string;
  message: string;
};

export function ErrorDisplay({
  title = "Something went wrong",
  message,
}: ErrorDisplayProps) {
  return (
    <div className="card border-brand-error/30 bg-brand-error/5">
      <h4>{title}</h4>
      <p className="mt-2 text-secondary">{message}</p>
    </div>
  );
}

