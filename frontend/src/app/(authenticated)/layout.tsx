import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

import { NGOINFO_LOGO_URL } from "@/lib/brand";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/profile", label: "My Profile" },
  { href: "/billing", label: "Plans & Billing" },
];

export default function AuthenticatedLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-brand-app-bg">
      <div className="grid min-h-screen md:grid-cols-[280px_1fr]">
        <aside className="border-r border-brand-border bg-brand-card-bg">
          <div className="border-b border-brand-border px-4 py-4 md:px-6">
            <Image
              src={NGOINFO_LOGO_URL}
              alt="NGOInfo"
              width={180}
              height={40}
              className="h-8 w-auto md:h-10"
              priority
            />
          </div>
          <nav className="space-y-1 p-4 md:p-6">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block rounded-[8px] px-4 py-2 text-[16px] font-medium text-brand-text-primary hover:bg-brand-divider"
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="px-4 pb-6 md:px-6">
            <button
              type="button"
              className="h-11 w-full rounded-[8px] border border-brand-border bg-transparent px-4 text-left text-sm font-medium text-brand-text-secondary"
            >
              Logout
            </button>
          </div>
        </aside>

        <div className="flex min-h-screen flex-col">
          <header className="border-b border-brand-border bg-brand-card-bg px-4 py-4 md:px-8">
            <p className="text-secondary">Authenticated workspace layout (UI stub)</p>
          </header>
          <main className="flex-1 px-4 py-6 md:px-8 md:py-8">{children}</main>
        </div>
      </div>
    </div>
  );
}

