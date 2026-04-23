import * as Tooltip from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface GlossaryTooltipProps {
  text: string;
  description: string | null | undefined;
  className?: string;
  children?: ReactNode;
}

export function GlossaryTooltip({ text, description, className, children }: GlossaryTooltipProps) {
  if (!description) {
    return <span className={className}>{children ?? text}</span>;
  }
  return (
    <Tooltip.Provider delayDuration={150}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <span
            className={cn(
              "underline decoration-dotted decoration-charcoal-40 underline-offset-2 cursor-help",
              className,
            )}
          >
            {children ?? text}
          </span>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            sideOffset={6}
            className="max-w-sm rounded-comfortable border border-cream-border bg-cream-light px-3 py-2 text-xs text-charcoal-82 shadow-focus z-50"
          >
            {description}
            <Tooltip.Arrow className="fill-cream-border" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}
