import { Badge } from "@/components/ui/badge";

const GRADE_STYLES: Record<string, string> = {
  S: "bg-yellow-400 text-yellow-900 font-bold",
  A: "bg-emerald-500 text-white font-bold",
  B: "bg-blue-500 text-white",
  C: "bg-orange-400 text-white",
  D: "bg-red-500 text-white",
};

export function ScoreBadge({ grade, size = "sm" }: { grade: string; size?: "sm" | "lg" }) {
  const sizeClass = size === "lg" ? "text-2xl px-4 py-1" : "";
  return (
    <Badge className={`${GRADE_STYLES[grade] ?? "bg-gray-400 text-white"} ${sizeClass}`}>
      {grade}
    </Badge>
  );
}
