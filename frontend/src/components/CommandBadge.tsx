import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function CommandBadge({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <code
      className={cn(
        "inline-flex max-w-full items-center rounded-md border bg-muted px-1.5 py-0.5 font-mono text-[0.9em] font-semibold leading-none text-foreground shadow-sm",
        className,
      )}
    >
      {children}
    </code>
  );
}
