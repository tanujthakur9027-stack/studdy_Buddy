import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Quiz — StudyBuddy AI",
  description: "Kahoot-style timed quiz with live scoring, difficulty levels, and detailed answer review.",
};

export default function QuizLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
