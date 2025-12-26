'use client';

import { useQuery } from '@tanstack/react-query';
import { CreditCard, Check, ArrowRight, Receipt, Calendar } from 'lucide-react';
import api from '@/lib/api';

const plans = [
  {
    name: 'Starter',
    price: 49,
    tier: 'starter',
    features: ['5 websites', '100 audits/month', 'Basic reports', 'Email support'],
  },
  {
    name: 'Pro',
    price: 149,
    tier: 'pro',
    popular: true,
    features: [
      '25 websites',
      '500 audits/month',
      'Advanced reports',
      'Priority support',
      'API access',
      'White-label reports',
    ],
  },
  {
    name: 'Enterprise',
    price: 399,
    tier: 'enterprise',
    features: [
      '100 websites',
      'Unlimited audits',
      'Custom reports',
      'Dedicated support',
      'API access',
      'White-label',
      'Custom integrations',
    ],
  },
  {
    name: 'Agency',
    price: 799,
    tier: 'agency',
    features: [
      'Unlimited websites',
      'Unlimited audits',
      'Client management',
      '24/7 support',
      'Full API access',
      'White-label everything',
      'Reseller dashboard',
      'Custom domain',
    ],
  },
];

export default function BillingPage() {
  const { data: subscription, isLoading } = useQuery({
    queryKey: ['subscription'],
    queryFn: () => api.getSubscription(),
  });

  const { data: payments } = useQuery({
    queryKey: ['payments'],
    queryFn: () => api.getPayments(),
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
        <h1 className="text-2xl font-bold text-gray-900">Billing</h1>
        <p className="mt-1 text-sm text-gray-500">Manage your subscription and payment methods</p>
      </div>

      {/* Current Plan */}
      {subscription && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Current Plan</h2>
              <p className="text-sm text-gray-500">
                {subscription.tier_name.charAt(0).toUpperCase() + subscription.tier_name.slice(1)}{' '}
                Plan
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-gray-900">
                ${(subscription.amount_cents / 100).toFixed(0)}
                <span className="text-sm font-normal text-gray-500">/month</span>
              </p>
              <p className="text-sm text-gray-500">
                Next billing: {new Date(subscription.current_period_end).toLocaleDateString()}
              </p>
            </div>
          </div>
          <div className="mt-4 flex items-center space-x-4">
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                subscription.status === 'active'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-yellow-100 text-yellow-800'
              }`}
            >
              {subscription.status}
            </span>
            <button className="text-sm text-blue-600 hover:text-blue-700">
              Manage subscription
            </button>
          </div>
        </div>
      )}

      {/* Plans */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          {subscription ? 'Upgrade Your Plan' : 'Choose a Plan'}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {plans.map((plan) => (
            <div
              key={plan.tier}
              className={`bg-white rounded-xl border-2 p-6 relative ${
                plan.popular ? 'border-blue-500' : 'border-gray-200'
              } ${subscription?.tier_name === plan.tier ? 'ring-2 ring-blue-500' : ''}`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-blue-500 text-white text-xs font-medium px-3 py-1 rounded-full">
                    Most Popular
                  </span>
                </div>
              )}

              <div className="text-center">
                <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
                <div className="mt-4">
                  <span className="text-4xl font-bold text-gray-900">${plan.price}</span>
                  <span className="text-gray-500">/month</span>
                </div>
              </div>

              <ul className="mt-6 space-y-3">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center text-sm">
                    <Check className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" />
                    <span className="text-gray-600">{feature}</span>
                  </li>
                ))}
              </ul>

              <button
                className={`mt-6 w-full py-2 px-4 rounded-lg font-medium transition-colors ${
                  subscription?.tier_name === plan.tier
                    ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                    : plan.popular
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                }`}
                disabled={subscription?.tier_name === plan.tier}
              >
                {subscription?.tier_name === plan.tier ? 'Current Plan' : 'Get Started'}
                {subscription?.tier_name !== plan.tier && (
                  <ArrowRight className="w-4 h-4 inline ml-1" />
                )}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Payment History */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Payment History</h2>
        </div>

        <div className="divide-y divide-gray-200">
          {payments?.map((payment: any) => (
            <div key={payment.id} className="px-6 py-4 flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="p-2 bg-gray-100 rounded-lg">
                  <Receipt className="w-5 h-5 text-gray-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {payment.description || 'Subscription Payment'}
                  </p>
                  <p className="text-xs text-gray-500 flex items-center">
                    <Calendar className="w-3 h-3 mr-1" />
                    {new Date(payment.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900">
                  ${(payment.amount_cents / 100).toFixed(2)}
                </p>
                <span
                  className={`text-xs ${
                    payment.status === 'succeeded' ? 'text-green-600' : 'text-yellow-600'
                  }`}
                >
                  {payment.status}
                </span>
              </div>
            </div>
          ))}
        </div>

        {(!payments || payments.length === 0) && (
          <div className="px-6 py-12 text-center">
            <CreditCard className="w-12 h-12 text-gray-300 mx-auto" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">No payments yet</h3>
            <p className="mt-2 text-sm text-gray-500">Your payment history will appear here</p>
          </div>
        )}
      </div>
    </div>
  );
}
