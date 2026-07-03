"use client"

import { Bell, ChevronRight, LogOut, User, Settings, Mic } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export function Header({
  section = "Dashboard",
  page = "Production",
}: {
  section?: string
  page?: string
}) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-slate-800 bg-slate-950/80 px-4 backdrop-blur-md sm:px-6">
      <div className="flex items-center gap-2 text-sm">
        <span className="flex items-center gap-2 lg:hidden">
          <span className="flex size-7 items-center justify-center rounded-md bg-emerald-500 text-slate-950">
            <Mic className="size-4" aria-hidden="true" />
          </span>
        </span>
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5">
          <span className="text-slate-400">{section}</span>
          <ChevronRight className="size-4 text-slate-600" aria-hidden="true" />
          <span className="font-medium text-slate-100">{page}</span>
        </nav>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="relative text-slate-400 hover:bg-slate-800 hover:text-slate-100"
          aria-label="Notifications, 3 unread"
        >
          <Bell className="size-5" aria-hidden="true" />
          <span className="absolute right-1.5 top-1.5 flex size-2 items-center justify-center rounded-full bg-red-500 ring-2 ring-slate-950" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <button
                type="button"
                className="flex items-center gap-2 rounded-full p-0.5 transition-colors hover:bg-slate-800"
                aria-label="Open user menu"
              />
            }
          >
            <Avatar className="size-9">
              <AvatarImage src="/host-avatar.png" alt="" />
              <AvatarFallback className="bg-emerald-500/15 text-emerald-400">DR</AvatarFallback>
            </Avatar>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col">
                <span className="text-sm font-medium">Diana Reyes</span>
                <span className="text-xs text-muted-foreground">producer@pbcweekly.fm</span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem>
                <User data-icon="inline-start" />
                Profile
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Settings data-icon="inline-start" />
                Settings
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive">
              <LogOut data-icon="inline-start" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
