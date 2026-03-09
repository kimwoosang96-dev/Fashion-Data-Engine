"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "검색", icon: "🔍" },
  { href: "/watchlist", label: "관심목록", icon: "❤️" },
  { href: "/settings", label: "AI 설정", icon: "⚙️" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="w-48 shrink-0 border-r border-gray-200 bg-white flex flex-col">
      <div className="px-5 py-5 border-b border-gray-100">
        <p className="text-xs text-gray-400 font-semibold uppercase tracking-wide">Fashion</p>
        <p className="text-base font-bold text-gray-900 leading-tight">Search</p>
      </div>
      <ul className="flex-1 py-3 space-y-0.5 px-2">
        {links.map(({ href, label, icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <li key={href}>
              <Link
                href={href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  active
                    ? "bg-gray-900 text-white font-medium"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                <span>{icon}</span>
                <span>{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
