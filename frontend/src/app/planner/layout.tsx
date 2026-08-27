import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Revision Planner — StudyBuddy AI",
  description: "Generate a personalised day-by-day revision roadmap with concept sessions, practice quizzes, buffer and rest days. Track your progress with an interactive checklist.",
};

export default function PlannerLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
