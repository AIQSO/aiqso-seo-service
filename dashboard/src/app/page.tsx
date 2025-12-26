'use client';

import { useQuery } from '@tanstack/react-query';
import { Globe, FileSearch, AlertCircle, CheckCircle, TrendingUp, Clock } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';
import StatsCard from '@/components/StatsCard';
import ScoreCard from '@/components/ScoreCard';

export default function DashboardPage() {
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.getDashboard(),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Overview of your SEO performance across all websites
        </p>
      </div>

      {/* Score Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <ScoreCard
          title="Average SEO Score"
          score={dashboard?.avg_score || null}
          change={dashboard?.score_change}
          subtitle="Across all websites"
        />
        <StatsCard title="Total Websites" value={dashboard?.total_websites || 0} icon={Globe} />
        <StatsCard
          title="Open Issues"
          value={dashboard?.open_issues || 0}
          icon={AlertCircle}
          changeType="negative"
        />
        <StatsCard
          title="Audits This Month"
          value={dashboard?.audits_this_month || 0}
          icon={FileSearch}
        />
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Audits */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Recent Audits</h2>
            <Link href="/audits" className="text-sm text-blue-600 hover:text-blue-700">
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {dashboard?.recent_audits?.map((audit: any) => (
              <div
                key={audit.id}
                className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
              >
                <div className="flex items-center space-x-3">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      audit.score >= 80
                        ? 'bg-green-500'
                        : audit.score >= 60
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                    }`}
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{audit.domain}</p>
                    <p className="text-xs text-gray-500">
                      {new Date(audit.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <span
                  className={`text-sm font-semibold ${
                    audit.score >= 80
                      ? 'text-green-600'
                      : audit.score >= 60
                        ? 'text-yellow-600'
                        : 'text-red-600'
                  }`}
                >
                  {audit.score}/100
                </span>
              </div>
            )) || <p className="text-sm text-gray-500 text-center py-4">No recent audits</p>}
          </div>
        </div>

        {/* Top Issues */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Top Issues</h2>
            <Link href="/issues" className="text-sm text-blue-600 hover:text-blue-700">
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {dashboard?.top_issues?.map((issue: any) => (
              <div
                key={issue.id}
                className="flex items-start space-x-3 py-2 border-b border-gray-100 last:border-0"
              >
                <AlertCircle
                  className={`w-4 h-4 mt-0.5 ${
                    issue.severity === 'critical'
                      ? 'text-red-500'
                      : issue.severity === 'warning'
                        ? 'text-yellow-500'
                        : 'text-blue-500'
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{issue.title}</p>
                  <p className="text-xs text-gray-500">{issue.domain}</p>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded-full ${
                    issue.severity === 'critical'
                      ? 'bg-red-100 text-red-700'
                      : issue.severity === 'warning'
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-blue-100 text-blue-700'
                  }`}
                >
                  {issue.severity}
                </span>
              </div>
            )) || (
              <div className="text-center py-4">
                <CheckCircle className="w-8 h-8 text-green-500 mx-auto" />
                <p className="text-sm text-gray-500 mt-2">No issues found</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            href="/websites"
            className="flex items-center p-4 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
          >
            <Globe className="w-5 h-5 text-blue-600 mr-3" />
            <span className="text-sm font-medium text-gray-900">Add Website</span>
          </Link>
          <Link
            href="/audits"
            className="flex items-center p-4 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
          >
            <FileSearch className="w-5 h-5 text-blue-600 mr-3" />
            <span className="text-sm font-medium text-gray-900">Run Audit</span>
          </Link>
          <Link
            href="/worklog"
            className="flex items-center p-4 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
          >
            <Clock className="w-5 h-5 text-blue-600 mr-3" />
            <span className="text-sm font-medium text-gray-900">View Work Log</span>
          </Link>
          <Link
            href="/billing"
            className="flex items-center p-4 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
          >
            <TrendingUp className="w-5 h-5 text-blue-600 mr-3" />
            <span className="text-sm font-medium text-gray-900">Upgrade Plan</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
