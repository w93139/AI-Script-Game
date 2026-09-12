import * as React from "react"

import { cn } from "@/lib/utils"

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "placeholder:text-faint bg-panel text-paper flex field-sizing-content min-h-16 w-full rounded-md border border-line px-3 py-2 text-sm transition-[color,background-color,border-color,box-shadow] duration-150 outline-none focus-visible:border-mist/40 focus-visible:ring-mist/40 focus-visible:ring-[3px] hover:bg-raised disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
