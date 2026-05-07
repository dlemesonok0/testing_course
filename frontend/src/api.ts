import type { Dish, NutritionDraft, Product } from "./types";

const API_BASE = "http://127.0.0.1:8001";

type ApiValidationIssue = {
  loc?: Array<string | number>;
  msg?: string;
};

const FIELD_TRANSLATIONS: Record<string, string> = {
  name: "Название",
  calories: "Калории",
  protein: "Белки",
  fat: "Жиры",
  carbs: "Углеводы",
  portion_size_grams: "Размер порции",
  category: "Категория",
  cooking_state: "Степень готовности",
  quantity_grams: "Количество (г)",
  product_id: "Продукт",
  ingredients: "Состав",
};

const MSG_TRANSLATIONS: Record<string, string> = {
  "field required": "обязательно для заполнения",
  "value is not a valid float": "должно быть числом",
  "value is not a valid integer": "должно быть целым числом",
  "ensure this value has at least 2 characters": "минимум 2 символа",
  "ensure this value has at most 255 characters": "максимум 255 символов",
  "ensure this value is greater than 0": "должно быть больше 0",
  "ensure this value is greater than or equal to 0": "не может быть отрицательным",
  "ensure this value is less than or equal to": "не должно превышать",
  "less than or equal to": "не должно превышать",
  "greater than or equal to": "должно быть не меньше",
  "protein + fat + carbs must be less than or equal to 100": "сумма БЖУ не может быть больше 100",
  "protein + fat + carbs must be less than or equal to portion_size_grams": "сумма БЖУ не может быть больше веса порции",
};

function translateField(field: string | number): string {
  return FIELD_TRANSLATIONS[String(field)] ?? String(field);
}

function translateMessage(msg: string): string {
  for (const [eng, rus] of Object.entries(MSG_TRANSLATIONS)) {
    if (msg.toLowerCase().includes(eng.toLowerCase())) return rus;
  }
  return msg;
}

function formatApiErrorDetail(detail: unknown): string {
  if (!detail) return "Произошла неизвестная ошибка";
  if (typeof detail === "string") {
    if (detail === "Product is used in dishes") return "Нельзя удалить: продукт используется в блюдах";
    return translateMessage(detail);
  }

  // Handle Pydantic validation errors (list of objects)
  if (Array.isArray(detail)) {
    return detail
      .map((issue) => {
        if (!issue || typeof issue !== "object") return "";
        const typed = issue as ApiValidationIssue;
        const field = typed.loc?.[typed.loc.length - 1];
        const msg = typed.msg ? translateMessage(typed.msg) : "";
        if (field && msg) return `${translateField(field)}: ${msg}`;
        return msg;
      })
      .filter(Boolean)
      .join("; ");
  }

  // Handle custom error objects (like 409 Conflict)
  if (typeof detail === "object") {
    const d = detail as Record<string, any>;
    if ((d.detail === "Product is used in dishes" || d.detail === "Продукт используется в блюдах") && Array.isArray(d.dishes)) {
      const uniqueDishes = Array.from(new Set(d.dishes));
      return `Нельзя удалить: продукт используется в блюдах (${uniqueDishes.join(", ")})`;
    }
    return d.msg ? translateMessage(d.msg) : JSON.stringify(detail);
  }

  return String(detail);
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

export async function getNutritionDraft(
  ingredients: Array<{ product_id: number; quantity_grams: number }>,
  portionSizeGrams?: number,
) {
  const params = new URLSearchParams({ ingredients: JSON.stringify(ingredients) });
  if (portionSizeGrams !== undefined) {
    params.set("portion_size_grams", String(portionSizeGrams));
  }
  return parseJson<NutritionDraft>(await request(`${API_BASE}/dishes/nutrition-draft?${params.toString()}`));
}
