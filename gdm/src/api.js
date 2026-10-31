const TOKEN_KEY = "brightloop.auth.token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function apiRequest(path, { method = "GET", body, token = getToken(), signal } = {}) {
  if (!path.startsWith("/api/")) {
    throw new Error("API requests must use an /api/ route.");
  }

  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Token ${token}`;

  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("Could not reach the Brightloop API. Check that the backend is running.");
  }

  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message = typeof payload === "object" && payload !== null
      ? Object.entries(payload).map(([field, value]) => {
        const detail = Array.isArray(value) ? value.join(", ") : typeof value === "object" ? JSON.stringify(value) : String(value);
        return field === "detail" ? detail : `${field}: ${detail}`;
      }).join(" · ")
      : `Request failed (${response.status}).`;
    const error = new Error(message || `Request failed (${response.status}).`);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

export async function apiList(path, options) {
  const values = [];
  let next = path;
  const visited = new Set();

  while (next) {
    if (visited.has(next)) throw new Error("The API returned a repeated pagination link.");
    visited.add(next);
    const page = await apiRequest(next, options);
    if (!page || !Array.isArray(page.results)) {
      throw new Error(`The API response for ${path} did not match the paginated list contract.`);
    }
    values.push(...page.results);
    if (page.next) {
      const nextUrl = new URL(page.next, window.location.origin);
      next = `${nextUrl.pathname}${nextUrl.search}`;
      if (!nextUrl.pathname.startsWith("/api/")) {
        throw new Error("The API returned a pagination link outside /api/.");
      }
    } else {
      next = null;
    }
  }
  return values;
}
