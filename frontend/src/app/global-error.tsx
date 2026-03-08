"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html>
      <body className="bg-zinc-950 text-white">
        <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-start justify-center gap-4 px-6">
          <p className="text-xs uppercase tracking-[0.24em] text-zinc-400">Global Error</p>
          <h1 className="text-3xl font-black tracking-tight">예상치 못한 오류가 발생했습니다.</h1>
          <p className="text-sm text-zinc-300">
            오류는 추적 시스템에 기록되었습니다. 같은 동작을 다시 시도해도 반복되면 운영 로그를 확인해야 합니다.
          </p>
          <button
            type="button"
            onClick={() => reset()}
            className="rounded-full bg-white px-5 py-2 text-sm font-semibold text-zinc-950"
          >
            다시 시도
          </button>
        </main>
      </body>
    </html>
  );
}
