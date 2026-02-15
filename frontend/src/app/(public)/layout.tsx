import Image from "next/image";
import type { ReactNode } from "react";

import { NGOINFO_LOGO_URL } from "@/lib/brand";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-brand-app-bg">
      <header className="border-b border-brand-border bg-brand-card-bg">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 md:px-8">
          <Image
            src={NGOINFO_LOGO_URL}
            alt="NGOInfo"
            width={180}
            height={40}
            className="h-8 w-auto md:h-10"
            priority
          />
          <span className="text-secondary">GrantPilot Workspace</span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 md:px-8 md:py-12">{children}</main>
    </div>
  );
}

