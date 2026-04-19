import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Personal Research Assistant",
  description: "MemoRAG-powered research assistant with persistent memory and knowledge graphs",
};

const navItems = [
  { href: "/library", label: "Library", icon: "📚" },
  { href: "/graph", label: "Knowledge Graph", icon: "🕸️" },
  { href: "/chat", label: "Chat", icon: "💬" },
  { href: "/sessions", label: "Sessions", icon: "📅" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 min-h-screen">
        <div className="flex h-screen overflow-hidden">
          {/* Sidebar nav */}
          <nav className="w-56 bg-white border-r border-gray-200 flex flex-col shrink-0">
            {/* Logo */}
            <div className="px-5 py-5 border-b border-gray-100">
              <h1 className="text-sm font-bold text-gray-900 leading-tight">
                Research
                <br />
                <span className="text-blue-600">Assistant</span>
              </h1>
              <p className="text-xs text-gray-400 mt-0.5">
                MemoRAG · Knowledge Graph
              </p>
            </div>

            {/* Nav links */}
            <div className="flex-1 py-3 px-2 space-y-0.5">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
                >
                  <span>{item.icon}</span>
                  {item.label}
                </Link>
              ))}
            </div>

            {/* Footer */}
            <div className="px-4 py-3 border-t border-gray-100">
              <p className="text-xs text-gray-300">
                Powered by Claude Sonnet
              </p>
            </div>
          </nav>

          {/* Main content */}
          <main className="flex-1 overflow-y-auto p-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
