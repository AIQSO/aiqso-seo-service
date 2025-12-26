'use client';

import { useQuery } from '@tanstack/react-query';
import { Clock, Plus, DollarSign, Calendar, Tag } from 'lucide-react';
import api from '@/lib/api';
import { useState } from 'react';

const categoryColors: Record<string, string> = {
  audit: 'bg-blue-100 text-blue-800',
  fix: 'bg-green-100 text-green-800',
  optimization: 'bg-purple-100 text-purple-800',
  consultation: 'bg-yellow-100 text-yellow-800',
  monitoring: 'bg-gray-100 text-gray-800',
};

export default function WorklogPage() {
  const [showNewEntry, setShowNewEntry] = useState(false);

  const { data: worklog, isLoading } = useQuery({
    queryKey: ['worklog'],
    queryFn: () => api.getWorklog(),
  });

  const { data: summary } = useQuery({
    queryKey: ['worklog-summary'],
    queryFn: () => api.getWorklogSummary(),
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Work Log</h1>
          <p className="mt-1 text-sm text-gray-500">
            Track time and work performed for client billing
          </p>
        </div>
        <button
          onClick={() => setShowNewEntry(true)}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4 mr-2" />
          Log Work
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <Clock className="w-5 h-5 text-blue-600" />
          </div>
          <div className="mt-4">
            <p className="text-sm text-gray-500">This Month</p>
            <p className="text-2xl font-semibold text-gray-900">
              {Math.floor((summary?.this_month_minutes || 0) / 60)}h{' '}
              {(summary?.this_month_minutes || 0) % 60}m
            </p>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <DollarSign className="w-5 h-5 text-green-600" />
          </div>
          <div className="mt-4">
            <p className="text-sm text-gray-500">Billable Amount</p>
            <p className="text-2xl font-semibold text-gray-900">
              ${((summary?.billable_amount_cents || 0) / 100).toLocaleString()}
            </p>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="mt-4">
            <p className="text-sm text-gray-500">Completed Tasks</p>
            <p className="text-2xl font-semibold text-gray-900">{summary?.completed_tasks || 0}</p>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="mt-4">
            <p className="text-sm text-gray-500">Active Projects</p>
            <p className="text-2xl font-semibold text-gray-900">{summary?.active_projects || 0}</p>
          </div>
        </div>
      </div>

      {/* Work Log Entries */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Work</h2>
        </div>

        <div className="divide-y divide-gray-200">
          {worklog?.entries?.map((entry: any) => (
            <div key={entry.id} className="px-6 py-4 hover:bg-gray-50">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    <h3 className="text-sm font-medium text-gray-900">{entry.title}</h3>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        categoryColors[entry.category] || 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {entry.category}
                    </span>
                  </div>
                  {entry.description && (
                    <p className="mt-1 text-sm text-gray-500">{entry.description}</p>
                  )}
                  <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                    <span className="flex items-center">
                      <Calendar className="w-3 h-3 mr-1" />
                      {new Date(entry.created_at).toLocaleDateString()}
                    </span>
                    {entry.project_name && (
                      <span className="flex items-center">
                        <Tag className="w-3 h-3 mr-1" />
                        {entry.project_name}
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">
                    {Math.floor(entry.actual_minutes / 60)}h {entry.actual_minutes % 60}m
                  </p>
                  <p className="text-sm text-green-600">
                    ${((entry.actual_minutes / 60) * (entry.hourly_rate_cents / 100)).toFixed(2)}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {(!worklog?.entries || worklog.entries.length === 0) && (
          <div className="px-6 py-12 text-center">
            <Clock className="w-12 h-12 text-gray-300 mx-auto" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">No work logged yet</h3>
            <p className="mt-2 text-sm text-gray-500">
              Start tracking your SEO work to generate invoices
            </p>
            <button
              onClick={() => setShowNewEntry(true)}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Log Work
            </button>
          </div>
        )}
      </div>

      {/* New Entry Modal */}
      {showNewEntry && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Log Work</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                <input
                  type="text"
                  placeholder="What did you work on?"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <select className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                  <option value="audit">Audit</option>
                  <option value="fix">Fix</option>
                  <option value="optimization">Optimization</option>
                  <option value="consultation">Consultation</option>
                  <option value="monitoring">Monitoring</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Hours</label>
                  <input
                    type="number"
                    min="0"
                    placeholder="0"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Minutes</label>
                  <input
                    type="number"
                    min="0"
                    max="59"
                    placeholder="0"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  rows={3}
                  placeholder="Details about the work performed..."
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setShowNewEntry(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Save Entry
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
