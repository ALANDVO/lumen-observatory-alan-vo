import { ReactNode } from 'react';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="container px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="16" cy="16" r="14" stroke="#2563eb" strokeWidth="2"/>
                <path d="M16 8V24M8 16H24" stroke="#2563eb" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              <h1 className="text-xl font-bold text-gray-900">Lumen Observatory</h1>
            </div>
            <nav className="flex items-center gap-4 text-sm">
              <span className="text-gray-500">Actor Substrate Observatory</span>
            </nav>
          </div>
        </div>
      </header>
      <main className="container px-4 py-6">
        {children}
      </main>
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="container px-4 py-4 text-center text-sm text-gray-500">
            Lumen Observatory \u2014 Alan Vo alanvo@gmail.com | AI & Machine Learning
        </div>
      </footer>
    </div>
  );
}