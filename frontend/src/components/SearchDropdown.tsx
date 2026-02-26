"use client";

import type { Brand, Product } from "@/lib/types";

interface SearchDropdownProps {
  brandResults: Brand[];
  productResults: Product[];
  onBrandClick: (brand: Brand) => void;
  onProductClick: (product: Product) => void;
}

export function SearchDropdown({
  brandResults,
  productResults,
  onBrandClick,
  onProductClick,
}: SearchDropdownProps) {
  if (brandResults.length === 0 && productResults.length === 0) return null;

  return (
    <div className="absolute z-20 mt-2 w-full rounded-lg border border-gray-200 bg-white shadow-lg overflow-hidden">
      {brandResults.length > 0 && (
        <div>
          <p className="px-3 py-2 text-xs font-semibold text-gray-500 bg-gray-50 border-b border-gray-100">
            브랜드
          </p>
          <ul>
            {brandResults.slice(0, 8).map((brand) => (
              <li key={brand.id}>
                <button
                  type="button"
                  className="w-full px-3 py-2.5 text-left hover:bg-gray-50"
                  onClick={() => onBrandClick(brand)}
                >
                  <p className="text-sm font-medium text-gray-900">{brand.name}</p>
                  <p className="text-xs text-gray-400">{brand.slug}</p>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {productResults.length > 0 && (
        <div>
          <p className="px-3 py-2 text-xs font-semibold text-gray-500 bg-gray-50 border-y border-gray-100">
            제품
          </p>
          <ul>
            {productResults.slice(0, 10).map((product) => (
              <li key={product.id}>
                <button
                  type="button"
                  className="w-full px-3 py-2.5 text-left hover:bg-gray-50"
                  onClick={() => onProductClick(product)}
                >
                  <p className="text-sm font-medium text-gray-900 line-clamp-1">{product.name}</p>
                  <p className="text-xs text-gray-400 line-clamp-1">{product.product_key ?? product.url}</p>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
