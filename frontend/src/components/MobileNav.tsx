"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "홈", icon: "●" },
  { href: "/sales", label: "세일", icon: "▲" },
  { href: "/drops", label: "드롭", icon: "■" },
  { href: "/?focus=search", label: "검색", icon: "⌕" },
  { href: "/feed", label: "피드", icon: "✦" },
];

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-black/10 bg-white/95 backdrop-blur md:hidden">
      <ul className="grid grid-cols-5">
        {links.map((item) => {
          const active = item.href === "/?focus=search"
            ? pathname === "/"
            : item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <li key={item.label}>
              <Link
                href={item.href}
                className={`flex min-h-14 flex-col items-center justify-center gap-1 px-2 text-[11px] font-medium ${
                  active ? "text-zinc-950" : "text-zinc-400"
                }`}
              >
                <span className="text-base leading-none">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
