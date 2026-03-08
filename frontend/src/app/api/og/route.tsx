import { ImageResponse } from "next/og";

export const runtime = "edge";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const name = searchParams.get("name") ?? "Fashion Data Engine";
  const price = searchParams.get("price") ?? "가격 확인";
  const brand = searchParams.get("brand") ?? "Streetwear Data";

  return new ImageResponse(
    (
      <div
        style={{
          width: "1200px",
          height: "630px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "linear-gradient(135deg, #111827 0%, #1f2937 55%, #d8ff63 100%)",
          color: "white",
          padding: "64px",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: 28, letterSpacing: 6, textTransform: "uppercase", opacity: 0.7 }}>
            Fashion Data Engine
          </div>
          <div
            style={{
              fontSize: 24,
              padding: "12px 22px",
              borderRadius: 999,
              background: "rgba(255,255,255,0.14)",
            }}
          >
            {brand}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div style={{ fontSize: 68, fontWeight: 800, lineHeight: 1.05, maxWidth: 900 }}>
            {name}
          </div>
          <div style={{ fontSize: 42, color: "#d8ff63", fontWeight: 700 }}>
            최저 {price}
          </div>
        </div>
        <div style={{ fontSize: 24, opacity: 0.72 }}>
          실시간 채널 가격 비교 · 세일 패턴 · 재고 인텔
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}
