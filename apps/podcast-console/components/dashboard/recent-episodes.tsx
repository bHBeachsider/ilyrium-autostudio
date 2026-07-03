"use client"

import { MoreHorizontal, Pencil, BarChart3, Link2 } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

const episodes = [
  { title: "Ep. 141 — The Inlet Dredging Debate", date: "Jun 1, 2026" },
  { title: "Ep. 140 — Snowbirds & the Housing Squeeze", date: "May 25, 2026" },
  { title: "Ep. 139 — Hurricane Season Prep 2026", date: "May 18, 2026" },
]

export function RecentEpisodes() {
  return (
    <Card className="border-slate-800 bg-slate-900">
      <CardHeader>
        <CardTitle className="text-slate-50">Recent Episodes</CardTitle>
        <CardDescription className="text-slate-400">Last 3 published episodes</CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow className="border-slate-800 hover:bg-transparent">
              <TableHead className="text-slate-400">Title</TableHead>
              <TableHead className="text-slate-400">Publish Date</TableHead>
              <TableHead className="text-slate-400">Status</TableHead>
              <TableHead className="w-12 text-right text-slate-400">
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {episodes.map((ep) => (
              <TableRow key={ep.title} className="border-slate-800 hover:bg-slate-800/40">
                <TableCell className="font-medium text-slate-100">{ep.title}</TableCell>
                <TableCell className="text-slate-400">{ep.date}</TableCell>
                <TableCell>
                  <Badge className="border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                    Published
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger
                      render={
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                          aria-label={`Actions for ${ep.title}`}
                        >
                          <MoreHorizontal className="size-4" aria-hidden="true" />
                        </Button>
                      }
                    />
                    <DropdownMenuContent align="end" className="w-48">
                      <DropdownMenuGroup>
                        <DropdownMenuItem>
                          <Pencil data-icon="inline-start" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <BarChart3 data-icon="inline-start" />
                          View Analytics
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Link2 data-icon="inline-start" />
                          Copy RSS Link
                        </DropdownMenuItem>
                      </DropdownMenuGroup>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
