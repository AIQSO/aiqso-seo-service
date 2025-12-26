'use client';

import { useQuery } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, Clock, Filter, ExternalLink } from 'lucide-react';
import api from '@/lib/api';
import { useState } from 'react';

const severityColors = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  warning: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  info: 'bg-blue-100 text-blue-800 border-blue-200',
};

const statusColors = {
  open: 'bg-red-100 text-red-800',
  in_progress: 'bg-yellow-100 text-yellow-800',
  resolved: 'bg-green-100 text-green-800',
};

export default function IssuesPage() {
  const [filter, setFilter] = useState<'all' | 'open' | 'in_progress' | 'resolved'>('all');
  const [severityFilter, setSeverityFilter] = useState<'all' | 'critical' | 'warning' | 'info'>(
    'all'
  );

  const { data: issues, isLoading } = useQuery({
    queryKey: ['issues'],
    queryFn: () => api.getIssues(),
  });

  const filteredIssues = issues?.filter((issue: any) => {
    if (filter !== 'all' && issue.status !== filter) return false;
    if (severityFilter !== 'all' && issue.severity !== severityFilter) return false;
    return true;
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const stats = {
    total: issues?.length || 0,
    critical: issues?.filter((i: any) => i.severity === 'critical').length || 0,
    warning: issues?.filter((i: any) => i.severity === 'warning').length || 0,
    open: issues?.filter((i: any) => i.status === 'open').length || 0,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Issues</h1>
        <p className="mt-1 text-sm text-gray-500">
          Track and resolve SEO issues across your websites
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Total Issues</p>
          <p className="text-2xl font-semibold text-gray-900">{stats.total}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Critical</p>
          <p className="text-2xl font-semibold text-red-600">{stats.critical}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Warnings</p>
          <p className="text-2xl font-semibold text-yellow-600">{stats.warning}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Open</p>
          <p className="text-2xl font-semibold text-blue-600">{stats.open}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-500">Status:</span>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-500">Severity:</span>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as any)}
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>
        </div>
      </div>

      {/* Issues List */}
      <div className="space-y-4">
        {filteredIssues?.map((issue: any) => (
          <div
            key={issue.id}
            className={`bg-white rounded-xl border ${
              issue.severity === 'critical'
                ? 'border-red-200'
                : issue.severity === 'warning'
                  ? 'border-yellow-200'
                  : 'border-gray-200'
            } p-6`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-4">
                <div
                  className={`p-2 rounded-lg ${
                    issue.severity === 'critical'
                      ? 'bg-red-100'
                      : issue.severity === 'warning'
                        ? 'bg-yellow-100'
                        : 'bg-blue-100'
                  }`}
                >
                  <AlertCircle
                    className={`w-5 h-5 ${
                      issue.severity === 'critical'
                        ? 'text-red-600'
                        : issue.severity === 'warning'
                          ? 'text-yellow-600'
                          : 'text-blue-600'
                    }`}
                  />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">{issue.title}</h3>
                  <p className="mt-1 text-sm text-gray-500">{issue.description}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${severityColors[issue.severity as keyof typeof severityColors]}`}
                    >
                      {issue.severity}
                    </span>
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[issue.status as keyof typeof statusColors]}`}
                    >
                      {issue.status.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-gray-500">{issue.domain}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {issue.fix_price_cents && (
                  <span className="text-sm font-medium text-green-600">
                    ${(issue.fix_price_cents / 100).toFixed(0)} to fix
                  </span>
                )}
                <button className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg">
                  <ExternalLink className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Recommendation */}
            {issue.recommendation && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                <p className="text-sm font-medium text-gray-700">Recommendation:</p>
                <p className="mt-1 text-sm text-gray-600">{issue.recommendation}</p>
              </div>
            )}

            {/* Actions */}
            <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-4">
              <div className="flex items-center text-xs text-gray-500">
                <Clock className="w-3 h-3 mr-1" />
                Found {new Date(issue.created_at).toLocaleDateString()}
              </div>
              <div className="flex space-x-2">
                {issue.status === 'open' && (
                  <button className="px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg">
                    Start Fix
                  </button>
                )}
                {issue.status === 'in_progress' && (
                  <button className="px-3 py-1.5 text-sm text-green-600 hover:bg-green-50 rounded-lg flex items-center">
                    <CheckCircle2 className="w-4 h-4 mr-1" />
                    Mark Resolved
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}

        {(!filteredIssues || filteredIssues.length === 0) && (
          <div className="bg-white rounded-xl border border-gray-200 px-6 py-12 text-center">
            <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">No issues found</h3>
            <p className="mt-2 text-sm text-gray-500">
              {filter !== 'all' || severityFilter !== 'all'
                ? 'Try adjusting your filters'
                : 'Your websites are looking great!'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
