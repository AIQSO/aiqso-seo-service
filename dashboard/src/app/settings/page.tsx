'use client';

import { useQuery } from '@tanstack/react-query';
import { User, Bell, Key, Link2, Shield, Save } from 'lucide-react';
import { useState } from 'react';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile');

  const tabs = [
    { id: 'profile', name: 'Profile', icon: User },
    { id: 'notifications', name: 'Notifications', icon: Bell },
    { id: 'api', name: 'API Keys', icon: Key },
    { id: 'integrations', name: 'Integrations', icon: Link2 },
    { id: 'security', name: 'Security', icon: Shield },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your account preferences and integrations
        </p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-64 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <tab.icon
                  className={`w-5 h-5 mr-3 ${
                    activeTab === tab.id ? 'text-blue-700' : 'text-gray-400'
                  }`}
                />
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === 'profile' && <ProfileSettings />}
          {activeTab === 'notifications' && <NotificationSettings />}
          {activeTab === 'api' && <ApiSettings />}
          {activeTab === 'integrations' && <IntegrationSettings />}
          {activeTab === 'security' && <SecuritySettings />}
        </div>
      </div>
    </div>
  );
}

function ProfileSettings() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">Profile Settings</h2>
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
            <input
              type="text"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="John"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
            <input
              type="text"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Doe"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="john@example.com"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
          <input
            type="text"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="AIQSO"
          />
        </div>
        <div className="flex justify-end">
          <button className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            <Save className="w-4 h-4 mr-2" />
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

function NotificationSettings() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">Notification Preferences</h2>
      <div className="space-y-4">
        {[
          {
            id: 'audit_complete',
            label: 'Audit Completed',
            description: 'Get notified when an audit finishes',
          },
          {
            id: 'score_drop',
            label: 'Score Drop Alert',
            description: 'Alert when SEO score drops significantly',
          },
          {
            id: 'weekly_report',
            label: 'Weekly Report',
            description: 'Receive weekly SEO summary emails',
          },
          {
            id: 'issue_critical',
            label: 'Critical Issues',
            description: 'Immediate alerts for critical SEO issues',
          },
        ].map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0"
          >
            <div>
              <p className="text-sm font-medium text-gray-900">{item.label}</p>
              <p className="text-sm text-gray-500">{item.description}</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" defaultChecked />
              <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
        ))}
      </div>
    </div>
  );
}

function ApiSettings() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">API Keys</h2>
      <p className="text-sm text-gray-500 mb-4">
        Use API keys to integrate with external tools and automate your workflows.
      </p>
      <div className="space-y-4">
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900">Production API Key</p>
              <p className="text-xs text-gray-500 mt-1">Created Dec 1, 2024</p>
            </div>
            <button className="text-sm text-red-600 hover:text-red-700">Revoke</button>
          </div>
          <div className="mt-3">
            <code className="text-sm bg-gray-200 px-3 py-1 rounded font-mono">
              sk_live_••••••••••••••••
            </code>
          </div>
        </div>
        <button className="flex items-center px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
          <Key className="w-4 h-4 mr-2" />
          Generate New Key
        </button>
      </div>
    </div>
  );
}

function IntegrationSettings() {
  const integrations = [
    { name: 'Odoo', status: 'connected', description: 'Sync clients and invoices' },
    { name: 'Stripe', status: 'connected', description: 'Process payments' },
    { name: 'Slack', status: 'disconnected', description: 'Get notifications in Slack' },
    { name: 'Google Analytics', status: 'disconnected', description: 'Import analytics data' },
    { name: 'Search Console', status: 'disconnected', description: 'Import search data' },
  ];

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">Integrations</h2>
      <div className="space-y-4">
        {integrations.map((integration) => (
          <div
            key={integration.name}
            className="flex items-center justify-between p-4 border border-gray-200 rounded-lg"
          >
            <div>
              <p className="text-sm font-medium text-gray-900">{integration.name}</p>
              <p className="text-sm text-gray-500">{integration.description}</p>
            </div>
            {integration.status === 'connected' ? (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Connected
              </span>
            ) : (
              <button className="px-4 py-1.5 text-sm text-blue-600 border border-blue-600 rounded-lg hover:bg-blue-50">
                Connect
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function SecuritySettings() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">Security Settings</h2>
      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-4">Change Password</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-700 mb-1">Current Password</label>
              <input
                type="password"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-700 mb-1">New Password</label>
              <input
                type="password"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-700 mb-1">Confirm New Password</label>
              <input
                type="password"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Update Password
            </button>
          </div>
        </div>

        <div className="border-t border-gray-200 pt-6">
          <h3 className="text-sm font-medium text-gray-900 mb-4">Two-Factor Authentication</h3>
          <p className="text-sm text-gray-500 mb-4">
            Add an extra layer of security to your account
          </p>
          <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
            Enable 2FA
          </button>
        </div>
      </div>
    </div>
  );
}
