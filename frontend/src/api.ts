import type { Dish, NutritionDraft, Product } from "./types";

const API_BASE = "http://127.0.0.1:8000";

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      detail = response.statusText;
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function assetUrl(path: string | null | undefined) {
  if (!path) return "";
  return `${API_BASE}${path}`;
}

export async function getProducts(query = "") {
  return parseJson<Product[]>(await fetch(`${API_BASE}/products${query}`));
}

export async function getProduct(id: number) {
  return parseJson<Product>(await fetch(`${API_BASE}/products/${id}`));
}

export async function createProduct(formData: FormData) {
  return parseJson<Product>(await fetch(`${API_BASE}/products`, { method: "POST", body: formData }));
}

export async function updateProduct(id: number, payload: Partial<Product>) {
  return parseJson<Product>(
    await fetch(`${API_BASE}/products/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  );
}

export async function deleteProduct(id: number) {
  const response = await fetch(`${API_BASE}/products/${id}`, { method: "DELETE" });
  if (response.status === 204) return;
  return parseJson(response);
}

export async function getDishes(query = "") {
  return parseJson<Dish[]>(await fetch(`${API_BASE}/dishes${query}`));
}

export async function getDish(id: number) {
  return parseJson<Dish>(await fetch(`${API_BASE}/dishes/${id}`));
}

export async function createDish(formData: FormData) {
  return parseJson<Dish>(await fetch(`${API_BASE}/dishes`, { method: "POST", body: formData }));
}

export async function updateDish(id: number, payload: Record<string, unknown>) {
  return parseJson<Dish>(
    await fetch(`${API_BASE}/dishes/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  );
}

export async function deleteDish(id: number) {
  const response = await fetch(`${API_BASE}/dishes/${id}`, { method: "DELETE" });
  if (response.status === 204) return;
  return parseJson(response);
}

export async function getNutritionDraft(ingredients: Array<{ product_id: number; quantity_grams: number }>) {
  const params = new URLSearchParams({ ingredients: JSON.stringify(ingredients) });
  return parseJson<NutritionDraft>(await fetch(`${API_BASE}/dishes/nutrition-draft?${params.toString()}`));
}
