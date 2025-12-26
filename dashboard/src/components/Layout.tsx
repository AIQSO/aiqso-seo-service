'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Globe,
  FileSearch,
  AlertCircle,
  Clock,
  CreditCard,
  Settings,
  LogOut,
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Websites', href: '/websites', icon: Globe },
  { name: 'Audits', href: '/audits', icon: FileSearch },
  { name: 'Issues', href: '/issues', icon: AlertCircle },
  { name: 'Work Log', href: '/worklog', icon: Clock },
  { name: 'Billing', href: '/billing', icon: CreditCard },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-200">
        {/* Logo */}
        <div className="flex items-center h-16 px-6 border-b border-gray-200">
          <span className="text-xl font-bold text-blue-600">AIQSO</span>
          <span className="ml-2 text-sm text-gray-500">SEO Platform</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-4 space-y-1">
          {navigation.map((item) => {
            const isActive =
              pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));

            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <item.icon
                  className={`w-5 h-5 mr-3 ${isActive ? 'text-blue-700' : 'text-gray-400'}`}
                />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-gray-200">
          <button className="flex items-center w-full px-3 py-2 text-sm text-gray-700 rounded-lg hover:bg-gray-100">
            <LogOut className="w-5 h-5 mr-3 text-gray-400" />
            Sign Out
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-64">
        <main className="p-8">{children}</main>
      </div>
    </div>
  );
}
