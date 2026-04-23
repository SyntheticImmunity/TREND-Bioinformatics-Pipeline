import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** shadcn-style class merger: clsx for conditional classes + tailwind-merge for de-duping. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
