import { ApiError } from '../types';

class ApiClient {
  private token: string | null = null;
  private baseUrl = '/redfish/v1';

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('hawkfish-token', token);
  }

  getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('hawkfish-token');
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('hawkfish-token');
  }

  private async request<T>(url: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      headers['X-Auth-Token'] = token;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorData: ApiError | null = null;
      try {
        errorData = await response.json();
      } catch {
        // Ignore JSON parse errors
      }

      const message = errorData?.error?.message || `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
    }

    // Handle empty responses
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  async login(username: string, password: string): Promise<void> {
    const response = await this.request<{ SessionToken: string }>(`${this.baseUrl}/SessionService/Sessions`, {
      method: 'POST',
      body: JSON.stringify({ UserName: username, Password: password }),
    });
    this.setToken(response.SessionToken);
  }

  async getSystems(page = 1, perPage = 50, filter = '') {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString(),
    });
    if (filter) {
      params.append('filter', filter);
    }
    return this.request(`${this.baseUrl}/Systems?${params}`);
  }

  async getSystem(id: string) {
    return this.request(`${this.baseUrl}/Systems/${id}`);
  }

  async powerAction(systemId: string, resetType: string) {
    return this.request(`${this.baseUrl}/Systems/${systemId}/Actions/ComputerSystem.Reset`, {
      method: 'POST',
      body: JSON.stringify({ ResetType: resetType }),
    });
  }

  async setBootOverride(systemId: string, target: string, persist = false) {
    return this.request(`${this.baseUrl}/Systems/${systemId}/Actions/ComputerSystem.SetDefaultBootOrder`, {
      method: 'POST',
      body: JSON.stringify({ 
        BootSourceOverrideTarget: target,
        BootSourceOverrideEnabled: persist ? 'Continuous' : 'Once'
      }),
    });
  }

  async getImages() {
    return this.request(`${this.baseUrl}/Oem/HawkFish/Images`);
  }

  async insertMedia(systemId: string, imageUrl: string) {
    return this.request(`${this.baseUrl}/Managers/HawkFish/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia`, {
      method: 'POST',
      body: JSON.stringify({ Image: imageUrl }),
    });
  }

  async ejectMedia(systemId: string) {
    return this.request(`${this.baseUrl}/Managers/HawkFish/VirtualMedia/Cd/Actions/VirtualMedia.EjectMedia`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  async getTasks() {
    return this.request(`${this.baseUrl}/TaskService/Tasks`);
  }

  async getTask(id: string) {
    return this.request(`${this.baseUrl}/TaskService/Tasks/${id}`);
  }

  createEventSource(): EventSource | null {
    const token = this.getToken();
    if (!token) return null;

    const eventSource = new EventSource(`${this.baseUrl}/EventService/Events?token=${encodeURIComponent(token)}`);
    return eventSource;
  }
}

export const apiClient = new ApiClient();
