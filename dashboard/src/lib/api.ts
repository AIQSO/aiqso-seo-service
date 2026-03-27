/**
 * API Client for AIQSO SEO Service Dashboard
 *
 * Uses native fetch (no axios dependency).
 * All methods match what the dashboard pages expect.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002/api/v1';

interface RequestOptions extends Omit<RequestInit, 'headers'> {
  params?: Record<string, string | number | boolean | undefined>;
  headers?: Record<string, string>;
}

class APIClient {
  private apiKey: string | null = null;

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    const key = this.getApiKey();
    if (key) {
      headers['X-API-Key'] = key;
    }

    return headers;
  }

  private async request<T = any>(
    path: string,
    options?: RequestOptions
  ): Promise<T> {
    const { params, headers: extraHeaders, ...fetchOptions } = options ?? {};

    let url = `${API_URL}${path}`;

    if (params) {
      const searchParams = new URLSearchParams();
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== null) {
          searchParams.set(key, String(value));
        }
      }
      const qs = searchParams.toString();
      if (qs) {
        url += `?${qs}`;
      }
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers: {
        ...this.getHeaders(),
        ...extraHeaders,
      },
    });

    if (!response.ok) {
      const body = await response.text();
      let detail: string;
      try {
        detail = JSON.parse(body).detail ?? body;
      } catch {
        detail = body;
      }
      throw new Error(`API ${response.status}: ${detail}`);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }

  // ---- Auth helpers ----

  setApiKey(key: string) {
    this.apiKey = key;
    if (typeof window !== 'undefined') {
      localStorage.setItem('seo_api_key', key);
    }
  }

  getApiKey(): string | null {
    if (!this.apiKey && typeof window !== 'undefined') {
      this.apiKey = localStorage.getItem('seo_api_key');
    }
    return this.apiKey;
  }

  clearApiKey() {
    this.apiKey = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('seo_api_key');
    }
  }

  // ---- Portal endpoints ----

  async getDashboard(): Promise<any> {
    return this.request('/portal/dashboard');
  }

  async getWebsites(): Promise<any[]> {
    return this.request('/portal/websites');
  }

  async getWebsiteAudits(websiteId: number, limit = 20): Promise<any[]> {
    return this.request(`/portal/websites/${websiteId}/audits`, {
      params: { limit },
    });
  }

  async getScoreHistory(websiteId: number, days = 30): Promise<any[]> {
    return this.request(`/portal/websites/${websiteId}/score-history`, {
      params: { days },
    });
  }

  async getWebsiteIssues(websiteId: number, status?: string): Promise<any[]> {
    return this.request(`/portal/websites/${websiteId}/issues`, {
      params: { status },
    });
  }

  async getAuditDetails(auditId: number): Promise<any> {
    return this.request(`/portal/audits/${auditId}`);
  }

  async requestAudit(websiteId: number, url?: string): Promise<any> {
    return this.request('/portal/audits/request', {
      method: 'POST',
      params: { website_id: websiteId, url },
    });
  }

  async getAccount(): Promise<any> {
    return this.request('/portal/account');
  }

  // ---- Billing endpoints ----

  async getPlans(): Promise<any> {
    return this.request('/billing/plans');
  }

  async getSubscription(): Promise<any> {
    return this.request('/billing/subscription');
  }

  async getUsage(): Promise<any> {
    return this.request('/billing/usage');
  }

  async createCheckout(tier: string, interval = 'monthly'): Promise<any> {
    return this.request('/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ tier, interval }),
    });
  }

  async getBillingPortal(): Promise<any> {
    return this.request('/billing/portal', { method: 'POST' });
  }

  async getPayments(limit = 20): Promise<any[]> {
    return this.request('/billing/payments', {
      params: { limit },
    });
  }

  // ---- Audit endpoints ----

  async getAudits(limit = 50): Promise<any[]> {
    return this.request('/portal/audits', {
      params: { limit },
    });
  }

  async runAudit(url: string): Promise<any> {
    return this.request('/audit', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  }

  // ---- Work log endpoints ----

  async getWorkLogs(params?: {
    status?: string;
    category?: string;
    limit?: number;
  }): Promise<any[]> {
    return this.request('/worklog/entries', { params });
  }

  async getWorkSummary(days = 30): Promise<any> {
    return this.request('/worklog/summary', {
      params: { days },
    });
  }

  async getProjects(status?: string): Promise<any[]> {
    return this.request('/worklog/projects', {
      params: { status },
    });
  }

  async getIssues(params?: {
    status?: string;
    website_id?: number;
    severity?: string;
  }): Promise<any[]> {
    return this.request('/worklog/issues', { params });
  }

  // ---- Convenience methods used by pages ----

  async getWorklog(): Promise<{ entries: any[] }> {
    const entries = await this.getWorkLogs({ limit: 50 });
    return { entries };
  }

  async getWorklogSummary(): Promise<any> {
    return this.getWorkSummary(30);
  }
}

export const api = new APIClient();
export default api;
