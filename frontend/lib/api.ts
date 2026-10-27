const API_URL = 'http://localhost:8000';

const getToken = () => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('token');
  }
  return null;
};

const authFetch = async (endpoint: string, options: RequestInit = {}) => {
  const token = getToken();
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (response.status === 401) {
    localStorage.removeItem('token');
    window.location.href = '/login';
    throw new Error('Session expired');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Error' }));
    throw new Error(error.detail || 'Error');
  }

  return response.json();
};

export const api = {
  login: async (email: string, password: string) => {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) throw new Error('Login failed');
    return response.json();
  },

  register: async (email: string, password: string) => {
    const response = await fetch(`${API_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) throw new Error('Register failed');
    return response.json();
  },

  getPlans: () => authFetch('/plans/'),
  getPlan: (id: number) => authFetch(`/plans/${id}`),
  generatePlan: (data: any) => authFetch('/plans/generate', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  logWorkout: (data: any) => authFetch('/workouts/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  getStats: () => authFetch('/workouts/'),
  updateProfile: (data: any) => authFetch('/users/me', {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
};