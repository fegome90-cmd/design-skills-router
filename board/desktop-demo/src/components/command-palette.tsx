import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandGroupLabel,
  CommandInput,
  CommandItem,
  CommandItemIcon,
  CommandItemText,
  CommandList,
  CommandShortcut,
} from "@ui-sdk/react/command"
import {
  Dialog,
  DialogBackdrop,
  DialogContent,
  DialogDescription,
  DialogShortcut,
  DialogTitle,
  DialogTrigger,
} from "@ui-sdk/react/dialog"
import { Search, type LucideIcon } from "lucide-react"
import type * as React from "react"

export type CommandAction = {
  id: string
  label: string
  icon: LucideIcon
  group: "Navegación" | "Acciones" | "Agente"
  shortcut?: string
  keywords?: string[]
  onSelect: () => void
}

const commandGroups: CommandAction["group"][] = [
  "Navegación",
  "Acciones",
  "Agente",
]

export function CommandPalette({
  open,
  onOpenChange,
  actions,
  triggerRef,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  actions: CommandAction[]
  triggerRef?: React.RefObject<HTMLButtonElement | null>
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger
        ref={triggerRef}
        data-size="sm"
        className="command-trigger"
        shortcut="mod+k"
        aria-label="Comandos"
        title="Comandos (⌘K)"
      >
        <Search aria-hidden="true" />
        <span className="toolbar-btn-label">Comandos</span>
        <DialogShortcut />
      </DialogTrigger>
      <DialogBackdrop />
      <DialogContent
        className="command-dialog"
        finalFocus={triggerRef ? () => triggerRef.current : undefined}
      >
        <DialogTitle className="sr-only">Paleta de comandos</DialogTitle>
        <DialogDescription className="sr-only">
          Busca vistas, acciones del espacio y flujos del agente.
        </DialogDescription>
        <Command
          onAction={(value) => {
            const item = actions.find((action) => action.id === value)
            if (item) {
              item.onSelect()
              onOpenChange(false)
            }
          }}
        >
          <div className="command-search" data-slot="row">
            <Search aria-hidden="true" />
            <CommandInput
              aria-label="Buscar comando"
              placeholder="Escribe un comando o sección…"
            />
          </div>
          <CommandEmpty>No se encontraron comandos.</CommandEmpty>
          <CommandList>
            {commandGroups.map((group) => {
              const groupActions = actions.filter(
                (action) => action.group === group
              )
              if (groupActions.length === 0) return null
              return (
                <CommandGroup key={group}>
                  <CommandGroupLabel>{group}</CommandGroupLabel>
                  {groupActions.map((action) => (
                    <CommandItem
                      key={action.id}
                      value={action.id}
                      label={action.label}
                      keywords={action.keywords}
                      shortcut={action.shortcut}
                    >
                      <CommandItemIcon>
                        <action.icon aria-hidden="true" />
                      </CommandItemIcon>
                      <CommandItemText>{action.label}</CommandItemText>
                      <CommandShortcut />
                    </CommandItem>
                  ))}
                </CommandGroup>
              )
            })}
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  )
}
