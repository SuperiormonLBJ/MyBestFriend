"use client";

import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/components/ui/avatar";
import type { ComponentProps, HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type MessageRole = "user" | "assistant";

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: MessageRole;
};

export const Message = ({ className, from, ...props }: MessageProps) => (
  <div
    className={cn(
      "group flex w-full items-end justify-end gap-2 py-4",
      from === "user" ? "is-user" : "is-assistant flex-row-reverse justify-end",
      "[&>div]:max-w-[80%]",
      className,
    )}
    {...props}
  />
);

export type MessageContentProps = HTMLAttributes<HTMLDivElement>;

export const MessageContent = ({
  children,
  className,
  ...props
}: MessageContentProps) => (
  <div
    className={cn(
      "flex flex-col gap-2 rounded-lg text-sm text-foreground px-4 py-3 overflow-hidden",
      "group-[.is-user]:bg-[#115e59] group-[.is-user]:text-[#ccfbf1] group-[.is-user]:border-[3px] group-[.is-user]:border-[#0d9488] group-[.is-user]:[box-shadow:4px_4px_0_0_#0d9488]",
      "group-[.is-assistant]:bg-[var(--surface)] group-[.is-assistant]:text-[var(--secondary)] group-[.is-assistant]:border-[3px] group-[.is-assistant]:border-[var(--border)] group-[.is-assistant]:[box-shadow:4px_4px_0_0_var(--border)]",
      className,
    )}
    {...props}
  >
    <div className="min-w-0">{children}</div>
  </div>
);

export type MessageAvatarProps = ComponentProps<typeof Avatar> & {
  src?: string;
  name?: string;
};

export const MessageAvatar = ({
  src,
  name,
  className,
  ...props
}: MessageAvatarProps) => (
  <Avatar
    className={cn("size-8 ring-1 ring-border shrink-0", className)}
    {...props}
  >
    <AvatarImage alt="" className="mt-0 mb-0" src={src} />
    <AvatarFallback>{name?.slice(0, 2) || "ME"}</AvatarFallback>
  </Avatar>
);
