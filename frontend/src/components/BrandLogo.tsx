import { cn } from "@/lib/utils";

export function BrandLogo({ className }: { className?: string }) {
  return (
    <img
      src="/brand-logo.png"
      alt=""
      aria-hidden="true"
      className={cn("h-10 w-10 rounded-xl object-cover", className)}
      draggable={false}
    />
  );
}
