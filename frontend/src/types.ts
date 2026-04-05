export type Product = {
  id: number;
  name: string;
  calories: number;
  protein: number;
  fat: number;
  carbs: number;
  composition: string | null;
  category: string;
  cooking_state: string;
  is_vegan: boolean;
  is_gluten_free: boolean;
  is_sugar_free: boolean;
  photo_url: string | null;
  photo_urls: string[];
  created_at: string;
  updated_at: string;
};

export type DishIngredient = {
  product_id: number;
  product_name: string;
  quantity_grams: number;
};

export type Dish = {
  id: number;
  name: string;
  description: string | null;
  category: string;
  portion_size_grams: number;
  calories: number;
  protein: number;
  fat: number;
  carbs: number;
  is_vegan: boolean;
  is_gluten_free: boolean;
  is_sugar_free: boolean;
  photo_url: string | null;
  photo_urls: string[];
  created_at: string;
  updated_at: string;
  ingredients: DishIngredient[];
  allowed_flags: string[];
};

export type NutritionDraft = {
  calories: number;
  protein: number;
  fat: number;
  carbs: number;
  allowed_flags: string[];
};
