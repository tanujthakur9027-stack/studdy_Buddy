import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "react-hot-toast";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "StudyBuddy — AI Personalized Learning Agent",
  description:
    "Upload your notes, get simplified explanations, play quiz games, and get a personalized revision plan powered by AI.",
  keywords: ["AI", "study", "quiz", "learning", "personalized", "RAG"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-gray-950">
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "#1f2937",
              color: "#f9fafb",
              border: "1px solid #374151",
              borderRadius: "12px",
            },
            success: { iconTheme: { primary: "#4361f5", secondary: "#fff" } },
            error: { iconTheme: { primary: "#ef4444", secondary: "#fff" } },
          }}
        />
        {children}
      </body>
    </html>
  );
}
