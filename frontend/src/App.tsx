import { useEffect, useRef, useState } from "react";
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

function getPhotoLimitError(selectedCount: number) {
  return selectedCount > MAX_PHOTOS ? `Можно выбрать не более ${MAX_PHOTOS} фотографий.` : "";
}

function formatNutrition(calories: number | string, protein: number | string, fat: number | string, carbs: number | string, caloriesLabel: string) {
  return `${calories} ${caloriesLabel} · Б ${protein} · Ж ${fat} · У ${carbs}`;
}

const TIMEZONE_SUFFIX_PATTERN = /(?:Z|[+-]\d{2}:?\d{2})$/i;

function getPreferredLocale() {
  if (typeof navigator === "undefined") return "ru-RU";
  return navigator.languages?.[0] ?? navigator.language ?? "ru-RU";
}

function parseTimestamp(value: string) {
  const trimmed = value.trim();
  const timestamp = TIMEZONE_SUFFIX_PATTERN.test(trimmed) ? trimmed : `${trimmed}Z`;
  const parsed = new Date(timestamp);
  return Number.isNaN(parsed.getTime()) ? new Date(value) : parsed;
}

function formatTimestamp(value: string) {
  const parsed = parseTimestamp(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat(getPreferredLocale(), {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(parsed);
}

function isSameTimestamp(left: string, right: string) {
  const leftDate = parseTimestamp(left);
  const rightDate = parseTimestamp(right);
  if (!Number.isNaN(leftDate.getTime()) && !Number.isNaN(rightDate.getTime())) {
    return leftDate.getTime() === rightDate.getTime();
  }
  return left.trim() === right.trim();
}

function formatDishSubtitle(category: string, portionSizeGrams: number | string) {
  const parts = [];
  if (category.trim()) parts.push(category);
  parts.push(`${portionSizeGrams} г / порция`);
  return parts.join(" · ");
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
  photos: [] as Array<{ url: string; file?: File }>,
};

const emptyDish = {
  name: "",
  description: "",
  category: "",
  portion_size_grams: "250",
  calories: "0",
  protein: "0",
  fat: "0",
  carbs: "0",
  is_vegan: false,
  is_gluten_free: false,
  is_sugar_free: false,
  photos: [] as Array<{ url: string; file?: File }>,
  ingredients: [{ product_id: 0, quantity_grams: "100" }] as IngredientInput[],
};

const flags = [
  ["is_vegan", "Веган", "vegan"],
  ["is_gluten_free", "Без глютена", "gluten_free"],
  ["is_sugar_free", "Без сахара", "sugar_free"],
] as const;

type FlagKey = (typeof flags)[number][0];
type FlagSource = { [key in FlagKey]: boolean };

function getActiveFlagLabels(source: FlagSource) {
  return flags.filter(([key]) => source[key]).map(([, label]) => label);
}

function FlagBadges({ labels, emptyLabel }: { labels: readonly string[]; emptyLabel?: string }) {
  if (!labels.length && !emptyLabel) return null;

  return (
    <div className="flag-badges">
      {labels.length > 0 ? (
        labels.map((label) => <span className="flag-badge" key={label}>{label}</span>)
      ) : (
        <span className="flag-badge flag-badge-muted">{emptyLabel}</span>
      )}
    </div>
  );
}

function photoFileKey(photo: File, index: number) {
  return `${photo.name}-${photo.size}-${photo.lastModified}-${index}`;
}

function PhotoGallery({ items, onRemove }: { items: Array<{ url: string; file?: File }>; onRemove: (index: number) => void }) {
  if (!items.length) return null;
  return (
    <div className="photo-grid-manage">
      {items.map((item, index) => (
        <div className="photo-manage-item" key={index}>
          <img src={item.url} alt={`photo-${index}`} />
          <button className="photo-remove-overlay" type="button" onClick={() => onRemove(index)}>×</button>
        </div>
      ))}
    </div>
  );
}

function PhotoUploadField({ items, onChange, onError }: { items: Array<{ url: string; file?: File }>; onChange: (items: Array<{ url: string; file?: File }>) => void; onError: (msg: string) => void }) {
  const handleFiles = (files: File[]) => {
    if (items.length + files.length > MAX_PHOTOS) {
      onError(`Нельзя загрузить более ${MAX_PHOTOS} фотографий.`);
      return;
    }
    const newItems = files.map(file => ({
      url: URL.createObjectURL(file),
      file
    }));
    onChange([...items, ...newItems]);
    onError("");
  };

  return (
    <div className="field photo-upload">
      <span>Фотографии (макс. {MAX_PHOTOS})</span>
      {items.length < MAX_PHOTOS && (
        <label className="file-picker">
          <input
            className="file-input"
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => {
              handleFiles(Array.from(e.currentTarget.files ?? []));
              e.currentTarget.value = "";
            }}
          />
          <span>Добавить фото</span>
        </label>
      )}
      <PhotoGallery
        items={items}
        onRemove={(index) => {
          const item = items[index];
          if (item.file) URL.revokeObjectURL(item.url);
          onChange(items.filter((_, idx) => idx !== index));
        }}
      />
    </div>
  );
}

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
        <label className="filter-field">
          <span>Сортировка по</span>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="name">Название</option>
            <option value="calories">{PRODUCT_CALORIES_LABEL}</option>
            <option value="protein">Белки</option>
            <option value="fat">Жиры</option>
            <option value="carbs">Углеводы</option>
            <option value="created_at">Дата создания</option>
          </select>
        </label>
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
          flags: getActiveFlagLabels(product),
          createdAt: product.created_at,
          updatedAt: product.updated_at,
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
        <label className="filter-field">
          <span>Сортировка по</span>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="name">Название</option>
            <option value="calories">{DISH_CALORIES_LABEL}</option>
            <option value="protein">Белки</option>
            <option value="fat">Жиры</option>
            <option value="carbs">Углеводы</option>
            <option value="created_at">Дата создания</option>
          </select>
        </label>
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
          subtitle: formatDishSubtitle(dish.category, dish.portion_size_grams),
          image: dish.photo_url,
          meta: formatNutrition(dish.calories, dish.protein, dish.fat, dish.carbs, DISH_CALORIES_LABEL),
          flags: getActiveFlagLabels(dish),
          createdAt: dish.created_at,
          updatedAt: dish.updated_at,
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

function Cards({ items }: { items: Array<{ id: number; title: string; subtitle: string; description?: string; image: string | null; meta: string; flags: string[]; createdAt: string; updatedAt: string; href: string; editHref: string; onDelete: () => void }> }) {
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
            {item.description && <p>{item.description}</p>}
            <FlagBadges labels={item.flags} />
            <p className="nutrition">{item.meta}</p>
            <AuditMeta createdAt={item.createdAt} updatedAt={item.updatedAt} />
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

function AuditMeta({ createdAt, updatedAt }: { createdAt: string; updatedAt: string }) {
  const showUpdatedAt = !isSameTimestamp(createdAt, updatedAt);

  return (
    <div className="audit-meta">
      <span>Создано: {formatTimestamp(createdAt)}</span>
      {showUpdatedAt && <span>Изменено: {formatTimestamp(updatedAt)}</span>}
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
      <FlagBadges labels={getActiveFlagLabels(item)} emptyLabel="Флаги не выбраны" />
      <p className="nutrition">{formatNutrition(item.calories, item.protein, item.fat, item.carbs, PRODUCT_CALORIES_LABEL)}</p>
      <AuditMeta createdAt={item.created_at} updatedAt={item.updated_at} />
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
      <Header title={item.name} subtitle={formatDishSubtitle(item.category, item.portion_size_grams)} />
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
      <p className="nutrition">{formatNutrition(item.calories, item.protein, item.fat, item.carbs, DISH_CALORIES_LABEL)}</p>
      <FlagBadges labels={getActiveFlagLabels(item)} emptyLabel="Флаги не выбраны" />
      <AuditMeta createdAt={item.created_at} updatedAt={item.updated_at} />
      <div className="panel">
        <h3>Состав блюда</h3>
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
          photos: item.photo_urls.map(url => ({ url: assetUrl(url) })),
        });
      }
    );
  }, [edit, id]);

  const submit = async () => {
    if (form.photos.length > MAX_PHOTOS) return;

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
      
      form.photos.forEach((item) => {
        if (item.file) {
          body.append("photos", item.file);
        } else {
          body.append("photo_links", item.url);
        }
      });

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

  const photoSelectionError = getPhotoLimitError(form.photos.length);
  const hasTooManyPhotos = form.photos.length > MAX_PHOTOS;

  return (
    <section>
      <Header title={edit ? "Редактирование продукта" : "Новый продукт"} subtitle={`Для продукта можно загрузить до ${MAX_PHOTOS} фотографий.`} />
      {photoSelectionError && <p className="error">{photoSelectionError}</p>}
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
        <PhotoUploadField items={form.photos} onChange={(items) => setForm((prev) => ({ ...prev, photos: items }))} onError={setError} />
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
  const [existingPhotoUrls, setExistingPhotoUrls] = useState<string[]>([]);
  const [draft, setDraft] = useState<NutritionDraft | null>(null);
  const [error, setError] = useState("");
  const manualNutritionEditedRef = useRef(false);
  const skipNextDraftNutritionApplyRef = useRef(false);

  useEffect(() => {
    void getProducts().then(setProducts);
  }, []);

  useEffect(() => {
    if (!edit || !id) return;
    void getDish(Number(id)).then((item) => {
      skipNextDraftNutritionApplyRef.current = true;
      setForm({
        name: item.name,
        description: "",
        category: item.category,
        portion_size_grams: String(item.portion_size_grams),
        calories: String(item.calories),
        protein: String(item.protein),
        fat: String(item.fat),
        carbs: String(item.carbs),
        is_vegan: item.is_vegan,
        is_gluten_free: item.is_gluten_free,
        is_sugar_free: item.is_sugar_free,
        photos: item.photo_urls.map(url => ({ url: assetUrl(url) })),
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
    const portionSizeGrams = Number(form.portion_size_grams);
    if (!payload.length || !Number.isFinite(portionSizeGrams) || portionSizeGrams <= 0) {
      setDraft(null);
      return;
    }
    manualNutritionEditedRef.current = false;
    void getNutritionDraft(payload, portionSizeGrams)
      .then((value) => {
        const skipNutritionApply = skipNextDraftNutritionApplyRef.current;
        skipNextDraftNutritionApplyRef.current = false;
        setDraft(value);
        setForm((prev) => ({
          ...prev,
          ...(skipNutritionApply || manualNutritionEditedRef.current
            ? {}
            : {
                calories: String(value.calories),
                protein: String(value.protein),
                fat: String(value.fat),
                carbs: String(value.carbs),
              }),
          is_vegan: value.allowed_flags.includes("vegan") ? prev.is_vegan : false,
          is_gluten_free: value.allowed_flags.includes("gluten_free") ? prev.is_gluten_free : false,
          is_sugar_free: value.allowed_flags.includes("sugar_free") ? prev.is_sugar_free : false,
        }));
      })
      .catch(() => {
        skipNextDraftNutritionApplyRef.current = false;
        setDraft(null);
      });
  }, [form.ingredients.map((item) => `${item.product_id}:${item.quantity_grams}`).join("|"), form.portion_size_grams]);

  const updateNutritionField = (field: "calories" | "protein" | "fat" | "carbs", value: string) => {
    manualNutritionEditedRef.current = true;
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const submit = async () => {
    if (form.photos.length > MAX_PHOTOS) return;

    const ingredients = form.ingredients.map((item) => ({
      product_id: item.product_id,
      quantity_grams: Number(item.quantity_grams),
    }));
    const category = form.category.trim();
    const body = new FormData();
    body.append("name", form.name);
    body.append("description", "");
    body.append("category", category);
    body.append("portion_size_grams", form.portion_size_grams);
    body.append("calories", form.calories);
    body.append("protein", form.protein);
    body.append("fat", form.fat);
    body.append("carbs", form.carbs);
    body.append("is_vegan", String(form.is_vegan));
    body.append("is_gluten_free", String(form.is_gluten_free));
    body.append("is_sugar_free", String(form.is_sugar_free));
    body.append("ingredients", JSON.stringify(ingredients));
    form.photos.forEach((item) => {
      if (item.file) {
        body.append("photos", item.file);
      } else {
        body.append("photo_links", item.url);
      }
    });
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
  const photoSelectionError = getPhotoLimitError(form.photos.length);
  const hasTooManyPhotos = form.photos.length > MAX_PHOTOS;

  return (
    <section>
      <Header title={edit ? "Редактирование блюда" : "Новое блюдо"} subtitle={`Пищевая ценность считается на одну порцию, фото можно загрузить до ${MAX_PHOTOS} штук.`} />
      {photoSelectionError && <p className="error">{photoSelectionError}</p>}
      {error && <p className="error">{error}</p>}
      <div className="form-grid">
        <Field label="Название" value={form.name} onChange={(value) => setForm((prev) => ({ ...prev, name: value }))} />
        <label className="field">
          <span>Категория</span>
          <select value={form.category} onChange={(e) => setForm((prev) => ({ ...prev, category: e.target.value }))}>
            <option value="">Без категории</option>
            {DISH_CATEGORIES.map((item) => <option value={item} key={item}>{item}</option>)}
          </select>
        </label>
        <Field label="Размер порции, г" value={form.portion_size_grams} onChange={(value) => setForm((prev) => ({ ...prev, portion_size_grams: value }))} type="number" />
        <Field label={DISH_CALORIES_LABEL} value={form.calories} onChange={(value) => updateNutritionField("calories", value)} type="number" />
        <Field label={DISH_PROTEIN_LABEL} value={form.protein} onChange={(value) => updateNutritionField("protein", value)} type="number" />
        <Field label={DISH_FAT_LABEL} value={form.fat} onChange={(value) => updateNutritionField("fat", value)} type="number" />
        <Field label={DISH_CARBS_LABEL} value={form.carbs} onChange={(value) => updateNutritionField("carbs", value)} type="number" />
        {flags.map(([key, label, apiFlag]) => (
          <label className="checkbox" key={key}>
            <input type="checkbox" disabled={!allowed.includes(apiFlag)} checked={form[key]} onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.checked }))} />
            {label}
          </label>
        ))}
        <PhotoUploadField items={form.photos} onChange={(items) => setForm((prev) => ({ ...prev, photos: items }))} onError={setError} />
      </div>
      <div className="panel">
        <div className="ingredients-header">
          <h3>Состав блюда</h3>
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

function Field({ label, value, onChange, multiline, type = "text", readOnly = false }: { label: string; value: string; onChange: (value: string) => void; multiline?: boolean; type?: string; readOnly?: boolean }) {
  return (
    <label className="field">
      <span>{label}</span>
      {multiline ? <textarea value={value} readOnly={readOnly} onChange={(e) => onChange(e.target.value)} /> : <input type={type} value={value} readOnly={readOnly} onChange={(e) => onChange(e.target.value)} />}
    </label>
  );
}
