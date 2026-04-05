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
const MAX_PHOTOS = 5;
const PRODUCT_CATEGORIES = ["Замороженный", "Мясной", "Овощи", "Зелень", "Специи", "Крупы", "Консервы", "Жидкость", "Сладости"];
const DISH_CATEGORIES = ["Десерт", "Первое", "Второе", "Напиток", "Салат", "Суп", "Перекус"];
const COOKING_STATES = ["Готовый к употреблению", "Полуфабрикат", "Требует приготовления"];
const PRODUCT_CALORIES_LABEL = "ккал / 100 г";
const DISH_CALORIES_LABEL = "ккал / порция";
const PRODUCT_PROTEIN_LABEL = "Белки, г / 100 г";
const PRODUCT_FAT_LABEL = "Жиры, г / 100 г";
const PRODUCT_CARBS_LABEL = "Углеводы, г / 100 г";
const DISH_PROTEIN_LABEL = "Белки, г / порция";
const DISH_FAT_LABEL = "Жиры, г / порция";
const DISH_CARBS_LABEL = "Углеводы, г / порция";

function limitPhotos(files: File[]) {
  return files.slice(0, MAX_PHOTOS);
}

function formatNutrition(calories: number | string, protein: number | string, fat: number | string, carbs: number | string, caloriesLabel: string) {
  return `${calories} ${caloriesLabel} · Б ${protein} · Ж ${fat} · У ${carbs}`;
}

const emptyProduct = {
  name: "",
  calories: "0",
  protein: "0",
  fat: "0",
  carbs: "0",
  composition: "",
  category: PRODUCT_CATEGORIES[0],
  cooking_state: COOKING_STATES[0],
  is_vegan: false,
  is_gluten_free: false,
  is_sugar_free: false,
  photos: [] as File[],
};

const emptyDish = {
  name: "",
  description: "",
  category: DISH_CATEGORIES[0],
  portion_size_grams: "250",
  calories: "0",
  protein: "0",
  fat: "0",
  carbs: "0",
  is_vegan: false,
  is_gluten_free: false,
  is_sugar_free: false,
  photos: [] as File[],
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
  const [cookingState, setCookingState] = useState(() => searchParams.get("cookingState") ?? "");
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
      if (cookingState) params.set("cookingState", cookingState);
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
  }, [debouncedSearch, category, cookingState, selectedFlags.join(","), sortBy, sortOrder]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (category) params.set("category", category);
    if (cookingState) params.set("cookingState", cookingState);
    selectedFlags.forEach((flag) => params.append("flags", flag));
    if (sortBy !== "name") params.set("sortBy", sortBy);
    if (sortOrder !== "asc") params.set("sortOrder", sortOrder);
    setSearchParams(params, { replace: true });
  }, [search, category, cookingState, selectedFlags, sortBy, sortOrder, setSearchParams]);

  return (
    <section>
      <Header title="Продукты" subtitle="Подстрочный поиск, CRUD и защита удаления." />
      <div className="panel filters">
        <input placeholder="Поиск по названию" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">Любая категория</option>
          {PRODUCT_CATEGORIES.map((item) => <option value={item} key={item}>{item}</option>)}
        </select>
        <select value={cookingState} onChange={(e) => setCookingState(e.target.value)}>
          <option value="">Любая готовность</option>
          {COOKING_STATES.map((item) => <option value={item} key={item}>{item}</option>)}
        </select>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="name">Название</option>
          <option value="calories">{PRODUCT_CALORIES_LABEL}</option>
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
          subtitle: `${product.category} · ${product.cooking_state}`,
          description: product.composition ?? "Состав не указан",
          image: product.photo_url,
          meta: formatNutrition(product.calories, product.protein, product.fat, product.carbs, PRODUCT_CALORIES_LABEL),
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
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">Любая категория</option>
          {DISH_CATEGORIES.map((item) => <option value={item} key={item}>{item}</option>)}
        </select>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="name">Название</option>
          <option value="calories">{DISH_CALORIES_LABEL}</option>
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
          subtitle: `${dish.category} · ${dish.portion_size_grams} г / порция`,
          description: dish.description ?? "Описание не указано",
          image: dish.photo_url,
          meta: formatNutrition(dish.calories, dish.protein, dish.fat, dish.carbs, DISH_CALORIES_LABEL),
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
      <Header title={item.name} subtitle={`${item.category} · ${item.cooking_state}`} />
      {item.photo_urls.length > 0 && (
        <div className="photo-gallery">
          <img className="hero" src={assetUrl(item.photo_urls[0])} alt={item.name} />
          {item.photo_urls.length > 1 && (
            <div className="photo-strip">
              {item.photo_urls.map((photoUrl, index) => (
                <img
                  className="photo-thumb"
                  key={`${photoUrl}-${index}`}
                  src={assetUrl(photoUrl)}
                  alt={`${item.name} ${index + 1}`}
                />
              ))}
            </div>
          )}
        </div>
      )}
      <p>{item.composition ?? "Состав не указан"}</p>
      <p className="nutrition">{formatNutrition(item.calories, item.protein, item.fat, item.carbs, PRODUCT_CALORIES_LABEL)}</p>
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
      <Header title={item.name} subtitle={`${item.category} · ${item.portion_size_grams} г / порция`} />
      {item.photo_urls.length > 0 && (
        <div className="photo-gallery">
          <img className="hero" src={assetUrl(item.photo_urls[0])} alt={item.name} />
          {item.photo_urls.length > 1 && (
            <div className="photo-strip">
              {item.photo_urls.map((photoUrl, index) => (
                <img
                  className="photo-thumb"
                  key={`${photoUrl}-${index}`}
                  src={assetUrl(photoUrl)}
                  alt={`${item.name} ${index + 1}`}
                />
              ))}
            </div>
          )}
        </div>
      )}
      <p>{item.description ?? "Описание не указано"}</p>
      <p className="nutrition">{formatNutrition(item.calories, item.protein, item.fat, item.carbs, DISH_CALORIES_LABEL)}</p>
      <div className="panel">
        <h3>Состав на одну порцию</h3>
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
  const [existingPhotoUrls, setExistingPhotoUrls] = useState<string[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!edit || !id) return;
    void getProduct(Number(id)).then((item) =>
      {
        setExistingPhotoUrls(item.photo_urls);
        setForm({
          name: item.name,
          calories: String(item.calories),
          protein: String(item.protein),
          fat: String(item.fat),
          carbs: String(item.carbs),
          composition: item.composition ?? "",
          category: item.category,
          cooking_state: item.cooking_state,
          is_vegan: item.is_vegan,
          is_gluten_free: item.is_gluten_free,
          is_sugar_free: item.is_sugar_free,
          photos: [],
        });
      }
    );
  }, [edit, id]);

  const submit = async () => {
    try {
      const body = new FormData();
      body.append("name", form.name);
      body.append("calories", form.calories);
      body.append("protein", form.protein);
      body.append("fat", form.fat);
      body.append("carbs", form.carbs);
      body.append("composition", form.composition);
      body.append("category", form.category);
      body.append("cooking_state", form.cooking_state);
      body.append("is_vegan", String(form.is_vegan));
      body.append("is_gluten_free", String(form.is_gluten_free));
      body.append("is_sugar_free", String(form.is_sugar_free));
      form.photos.forEach((photo) => body.append("photos", photo));

      if (edit && id) {
        const saved = await updateProduct(Number(id), body);
        navigate(`/products/${saved.id}`);
        return;
      }

      const saved = await createProduct(body);
      navigate(`/products/${saved.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
    }
  };

  return (
    <section>
      <Header title={edit ? "Редактирование продукта" : "Новый продукт"} subtitle={`Для продукта можно загрузить до ${MAX_PHOTOS} фотографий.`} />
      {error && <p className="error">{error}</p>}
      <div className="form-grid">
        <Field label="Название" value={form.name} onChange={(value) => setForm((prev) => ({ ...prev, name: value }))} />
        <label className="field">
          <span>Категория</span>
          <select value={form.category} onChange={(e) => setForm((prev) => ({ ...prev, category: e.target.value }))}>
            {PRODUCT_CATEGORIES.map((item) => <option value={item} key={item}>{item}</option>)}
          </select>
        </label>
        <Field label="Состав" value={form.composition} onChange={(value) => setForm((prev) => ({ ...prev, composition: value }))} multiline />
        <label className="field">
          <span>Степень готовности</span>
          <select value={form.cooking_state} onChange={(e) => setForm((prev) => ({ ...prev, cooking_state: e.target.value }))}>
            {COOKING_STATES.map((item) => <option value={item} key={item}>{item}</option>)}
          </select>
        </label>
        <Field label={PRODUCT_CALORIES_LABEL} value={form.calories} onChange={(value) => setForm((prev) => ({ ...prev, calories: value }))} type="number" />
        <Field label={PRODUCT_PROTEIN_LABEL} value={form.protein} onChange={(value) => setForm((prev) => ({ ...prev, protein: value }))} type="number" />
        <Field label={PRODUCT_FAT_LABEL} value={form.fat} onChange={(value) => setForm((prev) => ({ ...prev, fat: value }))} type="number" />
        <Field label={PRODUCT_CARBS_LABEL} value={form.carbs} onChange={(value) => setForm((prev) => ({ ...prev, carbs: value }))} type="number" />
        {flags.map(([key, label]) => (
          <label className="checkbox" key={key}>
            <input type="checkbox" checked={form[key]} onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.checked }))} />
            {label}
          </label>
        ))}
        <div className="field photo-upload">
          <span>Фотографии</span>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => {
              const photos = limitPhotos(Array.from(e.target.files ?? []));
              setError((e.target.files?.length ?? 0) > MAX_PHOTOS ? `Можно выбрать не более ${MAX_PHOTOS} фотографий.` : "");
              setForm((prev) => ({ ...prev, photos }));
            }}
          />
          {form.photos.length > 0 && (
            <div className="photo-list">
              {form.photos.map((photo) => (
                <span className="photo-chip" key={`${photo.name}-${photo.size}`}>
                  {photo.name}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
      {existingPhotoUrls.length > 0 && (
        <div className="panel">
          <div className="photo-strip">
            {existingPhotoUrls.map((photoUrl, index) => (
              <img className="photo-thumb" key={`${photoUrl}-${index}`} src={assetUrl(photoUrl)} alt={`product-photo-${index + 1}`} />
            ))}
          </div>
        </div>
      )}
      <button className="primary" onClick={() => void submit()}>Сохранить</button>
    </section>
  );
}

function DishForm({ edit = false }: { edit?: boolean }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[]>([]);
  const [form, setForm] = useState(emptyDish);
  const [existingPhotoUrls, setExistingPhotoUrls] = useState<string[]>([]);
  const [draft, setDraft] = useState<NutritionDraft | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void getProducts().then(setProducts);
  }, []);

  useEffect(() => {
    if (!edit || !id) return;
    void getDish(Number(id)).then((item) => {
      setExistingPhotoUrls(item.photo_urls);
      setForm({
        name: item.name,
        description: item.description ?? "",
        category: item.category,
        portion_size_grams: String(item.portion_size_grams),
        calories: String(item.calories),
        protein: String(item.protein),
        fat: String(item.fat),
        carbs: String(item.carbs),
        is_vegan: item.is_vegan,
        is_gluten_free: item.is_gluten_free,
        is_sugar_free: item.is_sugar_free,
        photos: [],
        ingredients: item.ingredients.map((ingredient) => ({
          product_id: ingredient.product_id,
          quantity_grams: String(ingredient.quantity_grams),
        })),
      });
    });
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
    const body = new FormData();
    body.append("name", form.name);
    body.append("description", form.description);
    if (category) body.append("category", category);
    body.append("portion_size_grams", form.portion_size_grams);
    body.append("calories", form.calories);
    body.append("protein", form.protein);
    body.append("fat", form.fat);
    body.append("carbs", form.carbs);
    body.append("is_vegan", String(form.is_vegan));
    body.append("is_gluten_free", String(form.is_gluten_free));
    body.append("is_sugar_free", String(form.is_sugar_free));
    body.append("ingredients", JSON.stringify(ingredients));
    form.photos.forEach((photo) => body.append("photos", photo));
    try {
      if (edit && id) {
        const saved = await updateDish(Number(id), body);
        navigate(`/dishes/${saved.id}`);
        return;
      }
      const saved = await createDish(body);
      navigate(`/dishes/${saved.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
    }
  };

  const allowed = draft?.allowed_flags ?? [];

  return (
    <section>
      <Header title={edit ? "Редактирование блюда" : "Новое блюдо"} subtitle={`Пищевая ценность считается на одну порцию, фото можно загрузить до ${MAX_PHOTOS} штук.`} />
      {error && <p className="error">{error}</p>}
      <div className="form-grid">
        <Field label="Название" value={form.name} onChange={(value) => setForm((prev) => ({ ...prev, name: value }))} />
        <label className="field">
          <span>Категория</span>
          <select value={form.category} onChange={(e) => setForm((prev) => ({ ...prev, category: e.target.value }))}>
            {DISH_CATEGORIES.map((item) => <option value={item} key={item}>{item}</option>)}
          </select>
        </label>
        <Field label="Описание" value={form.description} onChange={(value) => setForm((prev) => ({ ...prev, description: value }))} multiline />
        <Field label="Размер порции, г" value={form.portion_size_grams} onChange={(value) => setForm((prev) => ({ ...prev, portion_size_grams: value }))} type="number" />
        <Field label={DISH_CALORIES_LABEL} value={form.calories} onChange={(value) => setForm((prev) => ({ ...prev, calories: value }))} type="number" />
        <Field label={DISH_PROTEIN_LABEL} value={form.protein} onChange={(value) => setForm((prev) => ({ ...prev, protein: value }))} type="number" />
        <Field label={DISH_FAT_LABEL} value={form.fat} onChange={(value) => setForm((prev) => ({ ...prev, fat: value }))} type="number" />
        <Field label={DISH_CARBS_LABEL} value={form.carbs} onChange={(value) => setForm((prev) => ({ ...prev, carbs: value }))} type="number" />
        {flags.map(([key, label, apiFlag]) => (
          <label className="checkbox" key={key}>
            <input type="checkbox" disabled={!allowed.includes(apiFlag)} checked={form[key]} onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.checked }))} />
            {label}
          </label>
        ))}
        <div className="field photo-upload">
            <span>Фотографии</span>
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={(e) => {
                const photos = limitPhotos(Array.from(e.target.files ?? []));
                setError((e.target.files?.length ?? 0) > MAX_PHOTOS ? `Можно выбрать не более ${MAX_PHOTOS} фотографий.` : "");
                setForm((prev) => ({ ...prev, photos }));
              }}
            />
            {form.photos.length > 0 && (
              <div className="photo-list">
                {form.photos.map((photo) => (
                  <span className="photo-chip" key={`${photo.name}-${photo.size}`}>
                    {photo.name}
                  </span>
                ))}
              </div>
            )}
        </div>
      </div>
      {existingPhotoUrls.length > 0 && (
        <div className="panel">
          <div className="photo-strip">
            {existingPhotoUrls.map((photoUrl, index) => (
              <img className="photo-thumb" key={`${photoUrl}-${index}`} src={assetUrl(photoUrl)} alt={`dish-photo-${index + 1}`} />
            ))}
          </div>
        </div>
      )}
      <div className="panel">
        <div className="ingredients-header">
          <h3>Состав на одну порцию</h3>
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
      {draft && <div className="panel accent"><strong>Черновик КБЖУ на порцию:</strong> {draft.calories} / {draft.protein} / {draft.fat} / {draft.carbs}</div>}
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
