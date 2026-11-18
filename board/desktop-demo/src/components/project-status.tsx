import { Badge } from "@/components/ui/badge"

export function ProjectStatus({ status }: { status: string }) {
  return <Badge variant="outline" className="status-badge" data-status={status}><span aria-hidden="true" />{status}</Badge>
}
