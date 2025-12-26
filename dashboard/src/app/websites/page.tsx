'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Plus, ExternalLink, RefreshCw } from 'lucide-react';
import api from '@/lib/api';

export default function WebsitesPage() {
  const {
    data: websites,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['websites'],
    queryFn: () => api.getWebsites(),
  });

  const handleRequestAudit = async (websiteId: number) => {
    try {
      await api.requestAudit(websiteId);
      alert('Audit requested! Check back in a few minutes.');
      refetch();
    } catch (error) {
      alert('Failed to request audit');
    }
  };

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
          <h1 className="text-2xl font-bold text-gray-900">Websites</h1>
          <p className="mt-1 text-sm text-gray-500">Manage and monitor your tracked websites</p>
        </div>
        <button className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          <Plus className="w-4 h-4 mr-2" />
          Add Website
        </button>
      </div>

      {/* Websites Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {websites?.map((site: any) => (
          <div key={site.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {/* Header with score */}
            <div
              className={`px-6 py-4 ${
                site.last_audit_score >= 80
                  ? 'bg-green-50'
                  : site.last_audit_score >= 60
                    ? 'bg-yellow-50'
                    : 'bg-red-50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      site.status === 'healthy' ? 'bg-green-500' : 'bg-yellow-500'
                    }`}
                  />
                  <span className="font-semibold text-gray-900">{site.domain}</span>
                </div>
                <a
                  href={`https://${site.domain}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-400 hover:text-gray-600"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
              <div className="mt-2">
                <span
                  className={`text-3xl font-bold ${
                    site.last_audit_score >= 80
                      ? 'text-green-600'
                      : site.last_audit_score >= 60
                        ? 'text-yellow-600'
                        : 'text-red-600'
                  }`}
                >
                  {site.last_audit_score || 'N/A'}
                </span>
                <span className="text-gray-500 ml-1">/100</span>
              </div>
            </div>

            {/* Stats */}
            <div className="px-6 py-4 grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Issues</p>
                <p className="text-xl font-semibold text-red-600">{site.issues_count}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Warnings</p>
                <p className="text-xl font-semibold text-yellow-600">{site.warnings_count}</p>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
              <p className="text-xs text-gray-500">
                {site.last_audit_at
                  ? `Last audit: ${new Date(site.last_audit_at).toLocaleDateString()}`
                  : 'No audits yet'}
              </p>
              <div className="flex space-x-2">
                <button
                  onClick={() => handleRequestAudit(site.id)}
                  className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  title="Request new audit"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
                <Link
                  href={`/websites/${site.id}`}
                  className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  View Details
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>

      {(!websites || websites.length === 0) && (
        <div className="bg-white rounded-xl border border-gray-200 px-6 py-12 text-center">
          <Globe className="w-12 h-12 text-gray-300 mx-auto" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No websites yet</h3>
          <p className="mt-2 text-sm text-gray-500">
            Add your first website to start tracking SEO performance
          </p>
          <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Add Website
          </button>
        </div>
      )}
    </div>
  );
}

function Globe(props: any) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      {...props}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418"
      />
    </svg>
  );
}
