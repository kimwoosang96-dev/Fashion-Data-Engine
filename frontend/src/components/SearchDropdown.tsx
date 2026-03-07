"use client";

import type { SearchSuggestion } from "@/lib/types";

interface SearchDropdownProps {
  suggestions: SearchSuggestion[];
  activeIndex: number;
  onHover: (index: number) => void;
  onSelect: (item: SearchSuggestion) => void;
}

const SECTION_LABEL = {
  brand: "브랜드",
  product: "제품",
} as const;

const ICON = {
  brand: "🏷️",
  product: "🛍️",
} as const;

export function SearchDropdown({
  suggestions,
  activeIndex,
  onHover,
  onSelect,
}: SearchDropdownProps) {
  if (suggestions.length === 0) return null;

  let lastType: SearchSuggestion["type"] | null = null;

  return (
    <div className="absolute z-20 mt-2 w-full overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg">
      <ul>
        {suggestions.map((item, index) => {
          const showHeader = item.type !== lastType;
          lastType = item.type;
          return (
            <li key={`${item.type}-${item.slug ?? item.product_key ?? item.label}-${index}`}>
              {showHeader && (
                <p className="border-y border-gray-100 bg-gray-50 px-3 py-2 text-xs font-semibold text-gray-500">
                  {SECTION_LABEL[item.type]}
                </p>
              )}
              <button
                type="button"
                className={`flex w-full items-start gap-3 px-3 py-2.5 text-left ${
                  index === activeIndex ? "bg-gray-100" : "hover:bg-gray-50"
                }`}
                onMouseEnter={() => onHover(index)}
                onClick={() => onSelect(item)}
              >
                <span className="mt-0.5 text-sm">{ICON[item.type]}</span>
                <span className="min-w-0">
                  <p className="line-clamp-1 text-sm font-medium text-gray-900">{item.label}</p>
                  <p className="line-clamp-1 text-xs text-gray-400">
                    {item.type === "brand"
                      ? item.slug
                      : [item.channel_name, item.product_key ?? item.product_url]
                          .filter(Boolean)
                          .join(" · ")}
                  </p>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
