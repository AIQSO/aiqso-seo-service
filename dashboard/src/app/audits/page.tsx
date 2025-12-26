'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FileSearch, Plus, Download, Eye, Calendar, RefreshCw } from 'lucide-react';
import api from '@/lib/api';
import { useState } from 'react';

export default function AuditsPage() {
  const queryClient = useQueryClient();
  const [showNewAudit, setShowNewAudit] = useState(false);
  const [newUrl, setNewUrl] = useState('');

  const { data: audits, isLoading } = useQuery({
    queryKey: ['audits'],
    queryFn: () => api.getAudits(),
  });

  const runAuditMutation = useMutation({
    mutationFn: (url: string) => api.runAudit(url),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audits'] });
      setShowNewAudit(false);
      setNewUrl('');
    },
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
          <h1 className="text-2xl font-bold text-gray-900">Audits</h1>
          <p className="mt-1 text-sm text-gray-500">View audit history and run new SEO audits</p>
        </div>
        <button
          onClick={() => setShowNewAudit(true)}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Audit
        </button>
      </div>

      {/* New Audit Modal */}
      {showNewAudit && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Run New Audit</h2>
            <input
              type="url"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <div className="mt-4 flex justify-end space-x-3">
              <button
                onClick={() => setShowNewAudit(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => runAuditMutation.mutate(newUrl)}
                disabled={!newUrl || runAuditMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {runAuditMutation.isPending ? 'Running...' : 'Run Audit'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Audits Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Website
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Score
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Issues
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {audits?.map((audit: any) => (
              <tr key={audit.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <FileSearch className="w-4 h-4 text-gray-400 mr-2" />
                    <span className="text-sm font-medium text-gray-900">{audit.domain}</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
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
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex space-x-2">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                      {audit.critical_count} critical
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                      {audit.warning_count} warnings
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <div className="flex items-center">
                    <Calendar className="w-4 h-4 mr-1" />
                    {new Date(audit.created_at).toLocaleDateString()}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      audit.status === 'completed'
                        ? 'bg-green-100 text-green-800'
                        : audit.status === 'running'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {audit.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                  <div className="flex items-center justify-end space-x-2">
                    <button
                      className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                      title="View Details"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                      title="Download Report"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                    <button
                      className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                      title="Re-run Audit"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {(!audits || audits.length === 0) && (
          <div className="px-6 py-12 text-center">
            <FileSearch className="w-12 h-12 text-gray-300 mx-auto" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">No audits yet</h3>
            <p className="mt-2 text-sm text-gray-500">
              Run your first SEO audit to see results here
            </p>
            <button
              onClick={() => setShowNewAudit(true)}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Run Audit
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
