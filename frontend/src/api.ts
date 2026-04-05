import type { Dish, NutritionDraft, Product } from "./types";

const API_BASE = "http://127.0.0.1:8000";

type ApiValidationIssue = {
  loc?: Array<string | number>;
  msg?: string;
};

function formatApiErrorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((issue) => {
        if (!issue || typeof issue !== "object") return "";
        const typedIssue = issue as ApiValidationIssue;
        const field = typedIssue.loc?.[typedIssue.loc.length - 1];
        if (typedIssue.msg && field) return `${String(field)}: ${typedIssue.msg}`;
        return typedIssue.msg ?? "";
      })
      .filter(Boolean);
    if (messages.length > 0) return messages.join("; ");
  }
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return "Не удалось обработать запрос";
}

async function request(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch {
    throw new Error("Не удалось связаться с сервером. Проверьте, что backend запущен.");
  }
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = "Не удалось выполнить запрос";
    try {
      const body = await response.json();
      detail = formatApiErrorDetail(body.detail);
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function assetUrl(path: string | null | undefined) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${API_BASE}${path}`;
}

export async function getProducts(query = "") {
  return parseJson<Product[]>(await request(`${API_BASE}/products${query}`));
}

export async function getProduct(id: number) {
  return parseJson<Product>(await request(`${API_BASE}/products/${id}`));
}

export async function createProduct(formData: FormData) {
  return parseJson<Product>(await request(`${API_BASE}/products`, { method: "POST", body: formData }));
}

export async function updateProduct(id: number, payload: Partial<Product> | FormData) {
  const init =
    payload instanceof FormData
      ? { method: "PATCH", body: payload }
      : {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        };
  return parseJson<Product>(await request(`${API_BASE}/products/${id}`, init));
}

export async function deleteProduct(id: number) {
  const response = await request(`${API_BASE}/products/${id}`, { method: "DELETE" });
  if (response.status === 204) return;
  return parseJson(response);
}

export async function getDishes(query = "") {
  return parseJson<Dish[]>(await request(`${API_BASE}/dishes${query}`));
}

export async function getDish(id: number) {
  return parseJson<Dish>(await request(`${API_BASE}/dishes/${id}`));
}

export async function createDish(formData: FormData) {
  return parseJson<Dish>(await request(`${API_BASE}/dishes`, { method: "POST", body: formData }));
}

export async function updateDish(id: number, payload: Record<string, unknown> | FormData) {
  const init =
    payload instanceof FormData
      ? { method: "PATCH", body: payload }
      : {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        };
  return parseJson<Dish>(await request(`${API_BASE}/dishes/${id}`, init));
}

export async function deleteDish(id: number) {
  const response = await request(`${API_BASE}/dishes/${id}`, { method: "DELETE" });
  if (response.status === 204) return;
  return parseJson(response);
}

export async function getNutritionDraft(ingredients: Array<{ product_id: number; quantity_grams: number }>) {
  const params = new URLSearchParams({ ingredients: JSON.stringify(ingredients) });
  return parseJson<NutritionDraft>(await request(`${API_BASE}/dishes/nutrition-draft?${params.toString()}`));
}
