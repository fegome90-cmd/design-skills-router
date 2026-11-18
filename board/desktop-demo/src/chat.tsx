import { ArrowUp, Check, Copy, MessageSquare, Route, SquarePen } from "lucide-react"
import { useEffect, useRef, useState, type FormEvent } from "react"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { InputGroup, InputGroupAddon, InputGroupTextarea } from "@/components/ui/input-group"
import { SidebarGroup, SidebarGroupLabel, SidebarInput, SidebarMenu, SidebarMenuButton, SidebarMenuItem } from "@/components/ui/sidebar"
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
        <Button className="new-conversation" variant="outline" onClick={onCreate}>
          <SquarePen data-icon="inline-start" /> Nueva conversación
        </Button>
        <SidebarInput
          className="context-search"
          type="search"
          aria-label="Buscar conversaciones"
          placeholder="Buscar conversaciones"
          value={query}
          onChange={event => onSearch(event.target.value)}
        />
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
                <MessageSquare />
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

function MessageArticle({ message }: { message: Message }) {
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle")
  const assistant = message.role === "assistant"

  async function copyMessage() {
    const content = [...message.paragraphs, ...(message.points ?? []).map(point => `- ${point}`)]
    try {
      await navigator.clipboard.writeText(content.join("\n\n"))
      setCopyStatus("copied")
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
            <Button variant="ghost" size="icon-sm" aria-label="Copiar mensaje" title="Copiar mensaje" onClick={copyMessage}>
              {copyStatus === "copied" ? <Check /> : <Copy />}
            </Button>
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
}: {
  conversation: Conversation
  draft: string
  onDraft: (value: string) => void
  onSend: (value: string) => void
}) {
  const thread = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLTextAreaElement>(null)
  const messageCount = conversation.messages.length

  useEffect(() => {
    const region = thread.current
    if (region) region.scrollTop = region.scrollHeight
  }, [conversation.id, messageCount])

  useEffect(() => {
    const element = input.current
    if (!element) return
    element.style.height = "auto"
    element.style.height = `${Math.min(element.scrollHeight, 144)}px`
  }, [draft])

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!draft.trim()) return
    onSend(draft.trim())
    input.current?.focus()
  }

  return (
    <section className="chat-view" aria-label="Conversación">
      <div className="thread-scroll" ref={thread}>
        <div className="reading-column">
          <header className="thread-header">
            <p className="eyebrow">{conversation.date === "Ahora" ? "Conversación local" : "Conversación de ejemplo"}</p>
            <h1>{conversation.title}</h1>
          </header>
          <div className="thread-log" role="log" aria-label="Historial de mensajes">
            {conversation.messages.map(message => <MessageArticle key={message.id} message={message} />)}
          </div>
          {!messageCount && (
            <Empty className="empty-chat">
              <EmptyHeader>
                <EmptyMedia variant="icon"><MessageSquare /></EmptyMedia>
                <EmptyTitle role="heading" aria-level={2}>Una conversación nueva</EmptyTitle>
                <EmptyDescription>Escribe abajo para añadir un mensaje al historial local.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
        </div>
      </div>
      <div className="composer-footer">
        <form className="reading-column" onSubmit={submit}>
          <InputGroup className="composer">
            <InputGroupTextarea
              ref={input}
              value={draft}
              rows={1}
              aria-label="Escribe un mensaje"
              placeholder="Escribe un mensaje…"
              onChange={event => onDraft(event.target.value)}
              onKeyDown={event => {
                if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                  event.preventDefault()
                  event.currentTarget.form?.requestSubmit()
                }
              }}
            />
            <InputGroupAddon align="block-end" className="composer-actions">
              <span>Los mensajes se añaden al hilo local.</span>
              <Button type="submit" size="icon" aria-label="Enviar mensaje" disabled={!draft.trim()}><ArrowUp /></Button>
            </InputGroupAddon>
          </InputGroup>
          <p className="demo-note">Demostración sin conexión a un modelo de IA.</p>
        </form>
      </div>
    </section>
  )
}
