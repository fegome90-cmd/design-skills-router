import {
  Input,
  InputClear,
  InputGroup as SearchInputGroup,
} from "@ui-sdk/react/input"
import {
  ScrollArea,
  ScrollAreaContent,
  ScrollAreaScrollbar,
  ScrollAreaThumb,
  ScrollAreaViewport,
} from "@ui-sdk/react/scroll-area"
import { Textarea } from "@ui-sdk/react/textarea"
import { Button } from "@ui-sdk/react/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@ui-sdk/react/tooltip"
import { ArrowUp, Check, Copy, MessageSquare, Plus, Route, X } from "lucide-react"
import { useEffect, useRef, useState, type FormEvent } from "react"
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { SidebarGroup, SidebarGroupLabel, SidebarMenu, SidebarMenuButton, SidebarMenuItem } from "@/components/ui/sidebar"
import type { Conversation, Message } from "@/data"

export function ConversationList({
  conversations,
  selected,
  query,
  onSearch,
  onSelect,
  onCreate,
}: {
  conversations: Conversation[]
  selected: string
  query: string
  onSearch: (query: string) => void
  onSelect: (id: string) => void
  onCreate: () => void
}) {
  const recent = conversations.filter(thread =>
    thread.title.toLocaleLowerCase("es").includes(query.trim().toLocaleLowerCase("es"))
  )

  return (
    <>
      <div className="context-tools">
        <Button className="new-conversation" onClick={onCreate}>
          <Plus data-icon="inline-start" aria-hidden="true" /> Nueva conversación
        </Button>
        <SearchInputGroup className="context-search-group h-9 rounded-lg border-input bg-card">
          <Input
            className="context-search"
            type="search"
            aria-label="Buscar conversaciones"
            placeholder="Buscar conversaciones"
            value={query}
            onValueChange={onSearch}
          />
          {query && (
            <InputClear aria-label="Limpiar búsqueda">
              <X aria-hidden="true" />
            </InputClear>
          )}
        </SearchInputGroup>
      </div>
      <SidebarGroup className="context-group">
        <SidebarGroupLabel className="context-label">Recientes</SidebarGroupLabel>
        <SidebarMenu className="gap-1">
          {recent.map(thread => (
            <SidebarMenuItem key={thread.id}>
              <SidebarMenuButton
                className="context-row"
                isActive={thread.id === selected}
                aria-label={thread.title}
                aria-current={thread.id === selected ? "true" : undefined}
                onClick={() => onSelect(thread.id)}
              >
                <MessageSquare aria-hidden="true" />
                <span className="context-row-main">{thread.title}</span>
                <span className="context-meta">{thread.date}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
        {!recent.length && <p className="context-empty">Sin conversaciones que coincidan.</p>}
      </SidebarGroup>
    </>
  )
}

function MessageArticle({
  message,
  onNotify,
}: {
  message: Message
  onNotify?: (message: string) => void
}) {
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle")
  const assistant = message.role === "assistant"
  const copyLabel = copyStatus === "copied" ? "Respuesta copiada" : "Copiar respuesta"

  async function copyMessage() {
    const content = [...message.paragraphs, ...(message.points ?? []).map(point => `- ${point}`)]
    try {
      await navigator.clipboard.writeText(content.join("\n\n"))
      setCopyStatus("copied")
      onNotify?.("Respuesta copiada")
    } catch {
      setCopyStatus("failed")
    }
  }

  return (
    <article className={assistant ? "message assistant-message" : "message user-message"}>
      {assistant && <div className="assistant-mark" aria-hidden="true"><Route size={17} /></div>}
      <div className="message-body">
        <span className="message-author">{assistant ? "Asistente" : "Tú"}</span>
        <div className="message-content">
          {message.paragraphs.map((paragraph, i) => <p key={i}>{paragraph}</p>)}
          {message.points && <ul>{message.points.map(point => <li key={point}>{point}</li>)}</ul>}
        </div>
        {assistant && (
          <div className="message-actions">
            <Tooltip delay={400}>
              <TooltipTrigger
                render={
                  <Button
                    data-variant="ghost"
                    data-size="icon-sm"
                    aria-label={copyLabel}
                    onClick={copyMessage}
                  />
                }
              >
                {copyStatus === "copied" ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
              </TooltipTrigger>
              <TooltipContent side="top">{copyLabel}</TooltipContent>
            </Tooltip>
            <span role="status">{copyStatus === "copied" ? "Copiado" : copyStatus === "failed" ? "No se pudo copiar" : ""}</span>
          </div>
        )}
      </div>
    </article>
  )
}

export function ChatView({
  conversation,
  draft,
  onDraft,
  onSend,
  onNotify,
}: {
  conversation: Conversation
  draft: string
  onDraft: (value: string) => void
  onSend: (value: string) => void
  onNotify?: (message: string) => void
}) {
  const thread = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLTextAreaElement>(null)
  const messageCount = conversation.messages.length

  useEffect(() => {
    const region = thread.current
    if (region) region.scrollTop = region.scrollHeight
  }, [conversation.id, messageCount])

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!draft.trim()) return
    onSend(draft.trim())
    input.current?.focus()
  }

  return (
    <section className="chat-view" aria-label="Conversación">
      <ScrollArea className="thread-scroll-root min-h-0 flex-1 border-0 rounded-none" type="hover">
        <ScrollAreaViewport ref={thread} role="region" aria-label="Mensajes" className="thread-scroll">
          <ScrollAreaContent className="p-0">
            <div className="reading-column">
              <header className="thread-header">
                <p className="eyebrow">{conversation.origin === "local" ? "Conversación local" : "Conversación de ejemplo"}</p>
                <h1>{conversation.title}</h1>
              </header>
              <div className="thread-log" role="log" aria-label="Historial de mensajes">
                {conversation.messages.map((message) => (
                  <MessageArticle key={message.id} message={message} onNotify={onNotify} />
                ))}
              </div>
              {!messageCount && (
                <Empty className="empty-chat">
                  <EmptyHeader>
                    <EmptyMedia variant="icon"><MessageSquare aria-hidden="true" /></EmptyMedia>
                    <EmptyTitle role="heading" aria-level={2}>Una conversación nueva</EmptyTitle>
                    <EmptyDescription>Escribe abajo para añadir un mensaje al historial local.</EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
            </div>
          </ScrollAreaContent>
        </ScrollAreaViewport>
        <ScrollAreaScrollbar orientation="vertical">
          <ScrollAreaThumb />
        </ScrollAreaScrollbar>
      </ScrollArea>
      <div className="composer-footer">
        <form className="reading-column" onSubmit={submit}>
          <div className="composer" role="group" aria-label="Nuevo mensaje">
            <Textarea
              ref={input}
              className="composer-input"
              value={draft}
              onValueChange={onDraft}
              autoResize
              submitShortcut="enter"
              onSubmit={value => {
                if (!value.trim()) return
                onSend(value.trim())
                input.current?.focus()
              }}
              rows={1}
              aria-label="Escribe un mensaje"
              placeholder="Escribe un mensaje…"
            />
            <div className="composer-actions">
              <span>Los mensajes se añaden al hilo local.</span>
              <Button type="submit" data-variant="solid" data-size="icon" aria-label="Enviar mensaje" disabled={!draft.trim()}>
                <ArrowUp aria-hidden="true" />
              </Button>
            </div>
          </div>
          <p className="demo-note">Demostración sin conexión a un modelo de IA.</p>
        </form>
      </div>
    </section>
  )
}
