const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

let unauthorizedHandler = null;

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

async function request(endpoint, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
  } catch {
    throw new Error("Unable to reach the service. Please check that the API is running.");
  }

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    if (response.status === 401 && unauthorizedHandler && endpoint !== "/auth/login") {
      unauthorizedHandler();
    }

    const message = Array.isArray(data?.detail)
      ? data.detail.map((error) => `${error.loc?.slice(-1).join("")}: ${error.msg}`).join(", ")
      : data?.detail || "Something went wrong. Please try again.";

    throw new Error(message);
  }

  return data;
}

const authorized = (token) => ({
  Authorization: `Bearer ${token}`,
});

const filterQuery = (filters = {}) => {
  const params = new URLSearchParams();

  if (filters.status) params.set("status_filter", filters.status);
  if (filters.category) params.set("category", filters.category);
  if (filters.priority) params.set("priority", filters.priority);

  const query = params.toString();
  return query ? `?${query}` : "";
};

export const login = (email, password) =>
  request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

export const register = (name, email, password) =>
  request("/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });

export const getCurrentUser = (token) =>
  request("/auth/me", {
    headers: authorized(token),
  });

export const createComplaint = (complaint, token) =>
  request("/complaints/", {
    method: "POST",
    headers: authorized(token),
    body: JSON.stringify(complaint),
  });

export const getMyComplaints = (token) =>
  request("/complaints/", {
    headers: authorized(token),
  });

export const getAssignedComplaints = (token, filters) =>
  request(`/complaints/assigned${filterQuery(filters)}`, {
    headers: authorized(token),
  });

export const updateComplaintStatus = (id, status, token) =>
  request(`/complaints/${id}/status`, {
    method: "PATCH",
    headers: authorized(token),
    body: JSON.stringify({ status }),
  });

export const assignComplaint = (id, authority_id, token) =>
  request(`/complaints/${id}/assign`, {
    method: "PATCH",
    headers: authorized(token),
    body: JSON.stringify({ authority_id }),
  });

export const getComplaintHistory = (id, token) =>
  request(`/complaints/${id}/history`, {
    headers: authorized(token),
  });

export const getUsers = (token) =>
  request("/admin/users", {
    headers: authorized(token),
  });

export const updateUserStatus = (id, is_active, token) =>
  request(`/admin/users/${id}/status`, {
    method: "PATCH",
    headers: authorized(token),
    body: JSON.stringify({ is_active }),
  });

export const getAdminComplaints = (token, filters) =>
  request(`/admin/complaints${filterQuery(filters)}`, {
    headers: authorized(token),
  });
