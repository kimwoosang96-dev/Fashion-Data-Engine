"use client";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { Product } from "@/lib/types";

const krw = (n: number) => `₩${n.toLocaleString()}`;

interface Props {
  product: Product;
  channelName?: string;
  priceKrw?: number;
  originalPriceKrw?: number;
  discountRate?: number;
}

export function ProductCard({ product, channelName, priceKrw, originalPriceKrw, discountRate }: Props) {
  const hasCompare = !!product.product_key;
  const isSoldOut = !product.is_active;

  const inner = (
    <Card className={`hover:shadow-md transition-shadow cursor-pointer group ${isSoldOut ? "opacity-80" : ""}`}>
      <div className="aspect-square overflow-hidden rounded-t-lg bg-gray-100">
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.name}
            className={`w-full h-full object-cover group-hover:scale-105 transition-transform duration-300 ${isSoldOut ? "grayscale" : ""}`}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400 text-4xl">👕</div>
        )}
      </div>
      <CardContent className="p-3">
        <p className="text-xs text-gray-500 mb-1 truncate">{channelName ?? ""}</p>
        <p className="text-sm font-medium leading-snug line-clamp-2">{product.name}</p>
        <div className="flex items-center gap-2 mt-2">
          {priceKrw != null && (
            <span className="text-sm font-bold">{krw(priceKrw)}</span>
          )}
          {originalPriceKrw != null && (
            <span className="text-xs text-gray-400 line-through">{krw(originalPriceKrw)}</span>
          )}
          {discountRate != null && (
            <Badge variant="destructive" className="text-xs px-1.5 py-0">
              -{discountRate}%
            </Badge>
          )}
          {isSoldOut && (
            <Badge variant="outline" className="text-xs px-1.5 py-0 border-gray-300 text-gray-500">
              품절
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );

  if (hasCompare) {
    return (
      <Link href={`/compare/${encodeURIComponent(product.product_key!)}`}>
        {inner}
      </Link>
    );
  }
  return (
    <a href={product.url} target="_blank" rel="noopener noreferrer">
      {inner}
    </a>
  );
}
