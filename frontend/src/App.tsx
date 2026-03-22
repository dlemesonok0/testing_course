import { useEffect, useState } from "react";
import { Link, Route, Routes, useNavigate, useParams, useSearchParams } from "react-router-dom";

import {
  assetUrl,
  createDish,
  createProduct,
  deleteDish,
  deleteProduct,
  getDish,
  getDishes,
  getNutritionDraft,
  getProduct,
  getProducts,
  updateDish,
  updateProduct,
} from "./api";
import type { Dish, NutritionDraft, Product } from "./types";

function useDebouncedValue<T>(value: T, delay = 350) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

type IngredientInput = { product_id: number; quantity_grams: string };

const emptyProduct = {
  name: "",
  calories: "0",
  protein: "0",
  fat: "0",
  carbs: "0",
  composition: "",
  category: "",
  requires_cooking: false,
  is_vegan: false,
  is_gluten_free: false,
  is_sugar_free: false,
  photo: null as File | null,
};

const emptyDish = {
  name: "",
  description: "",
  category: "",
  servings: "1",
  calories: "0",
  protein: "0",
  fat: "0",
  carbs: "0",
  is_vegan: false,
  is_gluten_free: false,
  is_sugar_free: false,
  photo: null as File | null,
  ingredients: [{ product_id: 0, quantity_grams: "100" }] as IngredientInput[],
};

const flags = [
  ["is_vegan", "Веган", "vegan"],
  ["is_gluten_free", "Без глютена", "gluten_free"],
  ["is_sugar_free", "Без сахара", "sugar_free"],
] as const;

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>Книга рецептов</h1>
        <p>React-клиент для управления продуктами и блюдами.</p>
        <nav>
          <Link to="/">Продукты</Link>
          <Link to="/products/new">Новый продукт</Link>
          <Link to="/dishes">Блюда</Link>
          <Link to="/dishes/new">Новое блюдо</Link>
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<ProductList />} />
          <Route path="/products/new" element={<ProductForm />} />
          <Route path="/products/:id" element={<ProductCard />} />
          <Route path="/products/:id/edit" element={<ProductForm edit />} />
          <Route path="/dishes" element={<DishList />} />
          <Route path="/dishes/new" element={<DishForm />} />
          <Route path="/dishes/:id" element={<DishCard />} />
          <Route path="/dishes/:id/edit" element={<DishForm edit />} />
        </Routes>
      </main>
    </div>
  );
}

function ProductList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState<Product[]>([]);
  const [search, setSearch] = useState(() => searchParams.get("search") ?? "");
  const [category, setCategory] = useState(() => searchParams.get("category") ?? "");
  const [requiresCooking, setRequiresCooking] = useState(() => searchParams.get("requiresCooking") ?? "");
  const [selectedFlags, setSelectedFlags] = useState<string[]>(() => searchParams.getAll("flags"));
  const [sortBy, setSortBy] = useState(() => searchParams.get("sortBy") ?? "name");
  const [sortOrder, setSortOrder] = useState(() => searchParams.get("sortOrder") ?? "asc");
  const [error, setError] = useState("");
  const debouncedSearch = useDebouncedValue(search);

  const load = async () => {
    try {
      const params = new URLSearchParams();
      if (debouncedSearch) params.set("search", debouncedSearch);
      if (category) params.set("category", category);
      if (requiresCooking) params.set("requiresCooking", requiresCooking);
      selectedFlags.forEach((flag) => params.append("flags", flag));
      params.set("sortBy", sortBy);
      params.set("sortOrder", sortOrder);
      const query = params.toString() ? `?${params.toString()}` : "";
      setItems(await getProducts(query));
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    }
  };

  useEffect(() => {
    void load();
  }, [debouncedSearch, category, requiresCooking, selectedFlags.join(","), sortBy, sortOrder]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (category) params.set("category", category);
    if (requiresCooking) params.set("requiresCooking", requiresCooking);
    selectedFlags.forEach((flag) => params.append("flags", flag));
    if (sortBy !== "name") params.set("sortBy", sortBy);
    if (sortOrder !== "asc") params.set("sortOrder", sortOrder);
    setSearchParams(params, { replace: true });
  }, [search, category, requiresCooking, selectedFlags, sortBy, sortOrder, setSearchParams]);

  return (
    <section>
      <Header title="Продукты" subtitle="Подстрочный поиск, CRUD и защита удаления." />
      <div className="panel filters">
        <input placeholder="Поиск по названию" value={search} onChange={(e) => setSearch(e.target.value)} />
        <input placeholder="Категория" value={category} onChange={(e) => setCategory(e.target.value)} />
        <select value={requiresCooking} onChange={(e) => setRequiresCooking(e.target.value)}>
          <option value="">Любой вариант готовки</option>
          <option value="true">Требует готовки</option>
          <option value="false">Без готовки</option>
        </select>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="name">Название</option>
          <option value="calories">Калории</option>
          <option value="protein">Белки</option>
          <option value="fat">Жиры</option>
          <option value="carbs">Углеводы</option>
          <option value="created_at">Дата создания</option>
        </select>
        <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
          <option value="asc">По возрастанию</option>
          <option value="desc">По убыванию</option>
        </select>
        <FlagFilter value={selectedFlags} onChange={setSelectedFlags} />
      </div>
      {error && <p className="error">{error}</p>}
      <Cards
        items={items.map((product) => ({
          id: product.id,
          title: product.name,
          subtitle: product.category,
          description: product.composition,
          image: product.photo_url,
          meta: `${product.calories} ккал · Б ${product.protein} · Ж ${product.fat} · У ${product.carbs}`,
          href: `/products/${product.id}`,
          editHref: `/products/${product.id}/edit`,
          onDelete: async () => {
            try {
              await deleteProduct(product.id);
              await load();
            } catch (e) {
              setError(e instanceof Error ? e.message : "Ошибка удаления");
            }
          },
        }))}
      />
    </section>
  );
}

function DishList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState<Dish[]>([]);
  const [search, setSearch] = useState(() => searchParams.get("search") ?? "");
  const [category, setCategory] = useState(() => searchParams.get("category") ?? "");
  const [selectedFlags, setSelectedFlags] = useState<string[]>(() => searchParams.getAll("flags"));
  const [sortBy, setSortBy] = useState(() => searchParams.get("sortBy") ?? "name");
  const [sortOrder, setSortOrder] = useState(() => searchParams.get("sortOrder") ?? "asc");
  const [error, setError] = useState("");
  const debouncedSearch = useDebouncedValue(search);

  const load = async () => {
    try {
      const params = new URLSearchParams();
      if (debouncedSearch) params.set("search", debouncedSearch);
      if (category) params.set("category", category);
      selectedFlags.forEach((flag) => params.append("flags", flag));
      params.set("sortBy", sortBy);
      params.set("sortOrder", sortOrder);
      const query = params.toString() ? `?${params.toString()}` : "";
      setItems(await getDishes(query));
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    }
  };

  useEffect(() => {
    void load();
  }, [debouncedSearch, category, selectedFlags.join(","), sortBy, sortOrder]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (category) params.set("category", category);
    selectedFlags.forEach((flag) => params.append("flags", flag));
    if (sortBy !== "name") params.set("sortBy", sortBy);
    if (sortOrder !== "asc") params.set("sortOrder", sortOrder);
    setSearchParams(params, { replace: true });
  }, [search, category, selectedFlags, sortBy, sortOrder, setSearchParams]);

  return (
    <section>
      <Header title="Блюда" subtitle="Черновой расчет КБЖУ строится по составу." />
      <div className="panel filters">
        <input placeholder="Поиск по названию" value={search} onChange={(e) => setSearch(e.target.value)} />
        <input placeholder="Категория" value={category} onChange={(e) => setCategory(e.target.value)} />
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="name">Название</option>
          <option value="calories">Калории</option>
          <option value="protein">Белки</option>
          <option value="fat">Жиры</option>
          <option value="carbs">Углеводы</option>
          <option value="created_at">Дата создания</option>
        </select>
        <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
          <option value="asc">По возрастанию</option>
          <option value="desc">По убыванию</option>
        </select>
        <FlagFilter value={selectedFlags} onChange={setSelectedFlags} />
      </div>
      {error && <p className="error">{error}</p>}
      <Cards
        items={items.map((dish) => ({
          id: dish.id,
          title: dish.name,
          subtitle: `${dish.category} · ${dish.servings} порц.`,
          description: dish.description,
          image: dish.photo_url,
          meta: `${dish.calories} ккал · Б ${dish.protein} · Ж ${dish.fat} · У ${dish.carbs}`,
          href: `/dishes/${dish.id}`,
          editHref: `/dishes/${dish.id}/edit`,
          onDelete: async () => {
            try {
              await deleteDish(dish.id);
              await load();
            } catch (e) {
              setError(e instanceof Error ? e.message : "Ошибка удаления");
            }
          },
        }))}
      />
    </section>
  );
}

function Cards({ items }: { items: Array<{ id: number; title: string; subtitle: string; description: string; image: string | null; meta: string; href: string; editHref: string; onDelete: () => void }> }) {
  return (
    <div className="grid">
      {items.map((item) => (
        <article className="card" key={item.id}>
          {item.image && <img src={assetUrl(item.image)} alt={item.title} />}
          <div className="card-body">
            <div className="card-header">
              <h3>{item.title}</h3>
              <span>{item.subtitle}</span>
            </div>
            <p>{item.description}</p>
            <p className="nutrition">{item.meta}</p>
            <div className="actions">
              <Link to={item.href}>Открыть</Link>
              <Link to={item.editHref}>Редактировать</Link>
              <button onClick={() => void item.onDelete()}>Удалить</button>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function ProductCard() {
  const { id } = useParams();
  const [item, setItem] = useState<Product | null>(null);

  useEffect(() => {
    if (!id) return;
    void getProduct(Number(id)).then(setItem);
  }, [id]);

  if (!item) return <p>Загрузка...</p>;
  return (
    <section className="detail">
      <Header title={item.name} subtitle={item.category} />
      {item.photo_url && <img className="hero" src={assetUrl(item.photo_url)} alt={item.name} />}
      <p>{item.composition}</p>
      <p className="nutrition">{item.calories} ккал · Б {item.protein} · Ж {item.fat} · У {item.carbs}</p>
    </section>
  );
}

function DishCard() {
  const { id } = useParams();
  const [item, setItem] = useState<Dish | null>(null);

  useEffect(() => {
    if (!id) return;
    void getDish(Number(id)).then(setItem);
  }, [id]);

  if (!item) return <p>Загрузка...</p>;
  return (
    <section className="detail">
      <Header title={item.name} subtitle={`${item.category} · ${item.servings} порц.`} />
      {item.photo_url && <img className="hero" src={assetUrl(item.photo_url)} alt={item.name} />}
      <p>{item.description}</p>
      <p className="nutrition">{item.calories} ккал · Б {item.protein} · Ж {item.fat} · У {item.carbs}</p>
      <div className="panel">
        <h3>Состав</h3>
        <ul className="ingredients">
          {item.ingredients.map((ingredient) => (
            <li key={`${ingredient.product_id}-${ingredient.quantity_grams}`}>
              <span>{ingredient.product_name}</span>
              <span>{ingredient.quantity_grams} г</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function ProductForm({ edit = false }: { edit?: boolean }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState(emptyProduct);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!edit || !id) return;
    void getProduct(Number(id)).then((item) =>
      setForm({
        name: item.name,
        calories: String(item.calories),
        protein: String(item.protein),
        fat: String(item.fat),
        carbs: String(item.carbs),
        composition: item.composition,
        category: item.category,
        requires_cooking: item.requires_cooking,
        is_vegan: item.is_vegan,
        is_gluten_free: item.is_gluten_free,
        is_sugar_free: item.is_sugar_free,
        photo: null,
      })
    );
  }, [edit, id]);

  const submit = async () => {
    try {
      if (edit && id) {
        const saved = await updateProduct(Number(id), {
          name: form.name,
          calories: Number(form.calories),
          protein: Number(form.protein),
          fat: Number(form.fat),
          carbs: Number(form.carbs),
          composition: form.composition,
          category: form.category,
          requires_cooking: form.requires_cooking,
          is_vegan: form.is_vegan,
          is_gluten_free: form.is_gluten_free,
          is_sugar_free: form.is_sugar_free,
        });
        navigate(`/products/${saved.id}`);
        return;
      }

      const body = new FormData();
      Object.entries(form).forEach(([key, value]) => {
        if (key === "photo") {
          if (value) body.append("photo", value as File);
        } else {
          const serialized = typeof value === "boolean" ? (value ? "true" : "false") : String(value);
          body.append(key, serialized);
        }
      });
      const saved = await createProduct(body);
      navigate(`/products/${saved.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
    }
  };

  return (
    <section>
      <Header title={edit ? "Редактирование продукта" : "Новый продукт"} subtitle="Фото загружается только при создании, остальное редактируется через API." />
      {error && <p className="error">{error}</p>}
      <div className="form-grid">
        <Field label="Название" value={form.name} onChange={(value) => setForm((prev) => ({ ...prev, name: value }))} />
        <Field label="Категория" value={form.category} onChange={(value) => setForm((prev) => ({ ...prev, category: value }))} />
        <Field label="Состав" value={form.composition} onChange={(value) => setForm((prev) => ({ ...prev, composition: value }))} multiline />
        <Field label="Калории" value={form.calories} onChange={(value) => setForm((prev) => ({ ...prev, calories: value }))} type="number" />
        <Field label="Белки" value={form.protein} onChange={(value) => setForm((prev) => ({ ...prev, protein: value }))} type="number" />
        <Field label="Жиры" value={form.fat} onChange={(value) => setForm((prev) => ({ ...prev, fat: value }))} type="number" />
        <Field label="Углеводы" value={form.carbs} onChange={(value) => setForm((prev) => ({ ...prev, carbs: value }))} type="number" />
        <label className="checkbox"><input type="checkbox" checked={form.requires_cooking} onChange={(e) => setForm((prev) => ({ ...prev, requires_cooking: e.target.checked }))} />Требует готовки</label>
        {flags.map(([key, label]) => (
          <label className="checkbox" key={key}>
            <input type="checkbox" checked={form[key]} onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.checked }))} />
            {label}
          </label>
        ))}
        {!edit && <input type="file" accept="image/*" onChange={(e) => setForm((prev) => ({ ...prev, photo: e.target.files?.[0] ?? null }))} />}
      </div>
      <button className="primary" onClick={() => void submit()}>Сохранить</button>
    </section>
  );
}

function DishForm({ edit = false }: { edit?: boolean }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[]>([]);
  const [form, setForm] = useState(emptyDish);
  const [draft, setDraft] = useState<NutritionDraft | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void getProducts().then(setProducts);
  }, []);

  useEffect(() => {
    if (!edit || !id) return;
    void getDish(Number(id)).then((item) =>
      setForm({
        name: item.name,
        description: item.description,
        category: item.category,
        servings: String(item.servings),
        calories: String(item.calories),
        protein: String(item.protein),
        fat: String(item.fat),
        carbs: String(item.carbs),
        is_vegan: item.is_vegan,
        is_gluten_free: item.is_gluten_free,
        is_sugar_free: item.is_sugar_free,
        photo: null,
        ingredients: item.ingredients.map((ingredient) => ({
          product_id: ingredient.product_id,
          quantity_grams: String(ingredient.quantity_grams),
        })),
      })
    );
  }, [edit, id]);

  useEffect(() => {
    const payload = form.ingredients.filter((item) => item.product_id > 0 && Number(item.quantity_grams) > 0).map((item) => ({
      product_id: item.product_id,
      quantity_grams: Number(item.quantity_grams),
    }));
    if (!payload.length) {
      setDraft(null);
      return;
    }
    void getNutritionDraft(payload)
      .then((value) => {
        setDraft(value);
        setForm((prev) => ({
          ...prev,
          calories: String(value.calories),
          protein: String(value.protein),
          fat: String(value.fat),
          carbs: String(value.carbs),
          is_vegan: value.allowed_flags.includes("vegan") ? prev.is_vegan : false,
          is_gluten_free: value.allowed_flags.includes("gluten_free") ? prev.is_gluten_free : false,
          is_sugar_free: value.allowed_flags.includes("sugar_free") ? prev.is_sugar_free : false,
        }));
      })
      .catch(() => setDraft(null));
  }, [form.ingredients.map((item) => `${item.product_id}:${item.quantity_grams}`).join("|")]);

  const submit = async () => {
    const ingredients = form.ingredients.map((item) => ({
      product_id: item.product_id,
      quantity_grams: Number(item.quantity_grams),
    }));
    const category = form.category.trim();
    try {
      if (edit && id) {
        const payload: Record<string, unknown> = {
          name: form.name,
          description: form.description,
          servings: Number(form.servings),
          calories: Number(form.calories),
          protein: Number(form.protein),
          fat: Number(form.fat),
          carbs: Number(form.carbs),
          is_vegan: form.is_vegan,
          is_gluten_free: form.is_gluten_free,
          is_sugar_free: form.is_sugar_free,
          ingredients,
        };
        if (category) payload.category = category;
        const saved = await updateDish(Number(id), payload);
        navigate(`/dishes/${saved.id}`);
        return;
      }

      const body = new FormData();
      body.append("name", form.name);
      body.append("description", form.description);
      if (category) body.append("category", category);
      body.append("servings", form.servings);
      body.append("calories", form.calories);
      body.append("protein", form.protein);
      body.append("fat", form.fat);
      body.append("carbs", form.carbs);
      body.append("is_vegan", String(form.is_vegan));
      body.append("is_gluten_free", String(form.is_gluten_free));
      body.append("is_sugar_free", String(form.is_sugar_free));
      body.append("ingredients", JSON.stringify(ingredients));
      if (form.photo) body.append("photo", form.photo);
      const saved = await createDish(body);
      navigate(`/dishes/${saved.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
    }
  };

  const allowed = draft?.allowed_flags ?? [];

  return (
    <section>
      <Header title={edit ? "Редактирование блюда" : "Новое блюдо"} subtitle="Флаги доступны только если их допускает состав блюда." />
      {error && <p className="error">{error}</p>}
      <div className="form-grid">
        <Field label="Название" value={form.name} onChange={(value) => setForm((prev) => ({ ...prev, name: value }))} />
        <Field label="Категория" value={form.category} onChange={(value) => setForm((prev) => ({ ...prev, category: value }))} />
        <Field label="Описание" value={form.description} onChange={(value) => setForm((prev) => ({ ...prev, description: value }))} multiline />
        <Field label="Порции" value={form.servings} onChange={(value) => setForm((prev) => ({ ...prev, servings: value }))} type="number" />
        <Field label="Калории" value={form.calories} onChange={(value) => setForm((prev) => ({ ...prev, calories: value }))} type="number" />
        <Field label="Белки" value={form.protein} onChange={(value) => setForm((prev) => ({ ...prev, protein: value }))} type="number" />
        <Field label="Жиры" value={form.fat} onChange={(value) => setForm((prev) => ({ ...prev, fat: value }))} type="number" />
        <Field label="Углеводы" value={form.carbs} onChange={(value) => setForm((prev) => ({ ...prev, carbs: value }))} type="number" />
        {flags.map(([key, label, apiFlag]) => (
          <label className="checkbox" key={key}>
            <input type="checkbox" disabled={!allowed.includes(apiFlag)} checked={form[key]} onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.checked }))} />
            {label}
          </label>
        ))}
        {!edit && <input type="file" accept="image/*" onChange={(e) => setForm((prev) => ({ ...prev, photo: e.target.files?.[0] ?? null }))} />}
      </div>
      <div className="panel">
        <div className="ingredients-header">
          <h3>Ингредиенты</h3>
          <button onClick={() => setForm((prev) => ({ ...prev, ingredients: [...prev.ingredients, { product_id: 0, quantity_grams: "100" }] }))}>Добавить</button>
        </div>
        {form.ingredients.map((ingredient, index) => (
          <div className="ingredient-row" key={index}>
            <select value={ingredient.product_id} onChange={(e) => setForm((prev) => ({ ...prev, ingredients: prev.ingredients.map((item, idx) => idx === index ? { ...item, product_id: Number(e.target.value) } : item) }))}>
              <option value={0}>Выберите продукт</option>
              {products.map((product) => <option value={product.id} key={product.id}>{product.name}</option>)}
            </select>
            <input type="number" min="1" value={ingredient.quantity_grams} onChange={(e) => setForm((prev) => ({ ...prev, ingredients: prev.ingredients.map((item, idx) => idx === index ? { ...item, quantity_grams: e.target.value } : item) }))} />
            <button onClick={() => setForm((prev) => ({ ...prev, ingredients: prev.ingredients.filter((_, idx) => idx !== index) }))} disabled={form.ingredients.length === 1}>Удалить</button>
          </div>
        ))}
      </div>
      {draft && <div className="panel accent"><strong>Черновик КБЖУ:</strong> {draft.calories} / {draft.protein} / {draft.fat} / {draft.carbs}</div>}
      <button className="primary" onClick={() => void submit()}>Сохранить</button>
    </section>
  );
}

function Header({ title, subtitle }: { title: string; subtitle: string }) {
  return <header className="page-header"><h2>{title}</h2><p>{subtitle}</p></header>;
}

function FlagFilter({ value, onChange }: { value: string[]; onChange: (next: string[]) => void }) {
  const toggle = (flag: string) => {
    onChange(value.includes(flag) ? value.filter((item) => item !== flag) : [...value, flag]);
  };

  return (
    <div className="flag-filter">
      {flags.map(([, label, apiFlag]) => (
        <label className="checkbox" key={apiFlag}>
          <input type="checkbox" checked={value.includes(apiFlag)} onChange={() => toggle(apiFlag)} />
          {label}
        </label>
      ))}
    </div>
  );
}

function Field({ label, value, onChange, multiline, type = "text" }: { label: string; value: string; onChange: (value: string) => void; multiline?: boolean; type?: string }) {
  return (
    <label className="field">
      <span>{label}</span>
      {multiline ? <textarea value={value} onChange={(e) => onChange(e.target.value)} /> : <input type={type} value={value} onChange={(e) => onChange(e.target.value)} />}
    </label>
  );
}
