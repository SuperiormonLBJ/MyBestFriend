"use client";

import { EtherealShadow } from "@/components/ui/ethereal-shadow";
import { CHAT_BG, ETHEREAL_DEFAULT_COLOR, ETHEREAL_ANIMATION, ETHEREAL_NOISE } from "@/lib/constants";

export default function JobPreparationLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div
        className="relative min-h-0 flex-1 overflow-y-auto overflow-x-hidden"
        style={{ backgroundColor: CHAT_BG }}
      >
        <div className="relative min-h-full w-full">
          <div className="pointer-events-none absolute inset-0 flex w-full min-h-full justify-center items-stretch">
            <EtherealShadow
              color={ETHEREAL_DEFAULT_COLOR}
              animation={ETHEREAL_ANIMATION}
              noise={ETHEREAL_NOISE}
              sizing="fill"
            />
          </div>
          <div className="relative z-10">{children}</div>
        </div>
      </div>
    </div>
  );
}
