export const API_BASE = "http://127.0.0.1:8001";

export const productCategories = {
  frozen: "Замороженный",
  meat: "Мясной",
  vegetables: "Овощи",
};

export const dishCategories = {
  second: "Второе",
  salad: "Салат",
};

export const cookingStates = {
  ready: "Готовый к употреблению",
  needsCooking: "Требует приготовления",
};

export type ProductFormData = {
  name: string;
  composition?: string;
  category?: string;
  cookingState?: string;
  calories: string;
  protein: string;
  fat: string;
  carbs: string;
  isVegan?: boolean;
  isGlutenFree?: boolean;
  isSugarFree?: boolean;
};

export const validProduct = (suffix: string): ProductFormData => ({
  name: `UI Product ${suffix}`,
  composition: "Water, salt",
  category: productCategories.vegetables,
  cookingState: cookingStates.ready,
  calories: "42",
  protein: "2",
  fat: "1",
  carbs: "5",
  isVegan: true,
  isGlutenFree: true,
  isSugarFree: true,
});

export const productNutritionCases = [
  { id: "invalid-name-length-1", override: { name: "A" }, valid: false },
  { id: "invalid-blank-name", override: { name: "    " }, valid: false },
  { id: "valid-name-length-2", override: { name: "AB" }, valid: true },
  { id: "invalid-negative-calories", override: { calories: "-0.01" }, valid: false },
  { id: "valid-zero-calories", override: { calories: "0" }, valid: true },
  { id: "valid-positive-calories-boundary", override: { calories: "0.01" }, valid: true },
  { id: "valid-bju-sum-100", override: { protein: "40", fat: "30", carbs: "30" }, valid: true },
  { id: "invalid-bju-sum-100-01", override: { protein: "40", fat: "30", carbs: "30.01" }, valid: false },
  { id: "invalid-single-protein-100-01", override: { protein: "100.01", fat: "0", carbs: "0" }, valid: false },
  { id: "invalid-single-fat-100-01", override: { protein: "0", fat: "100.01", carbs: "0" }, valid: false },
  { id: "invalid-single-carbs-100-01", override: { protein: "0", fat: "0", carbs: "100.01" }, valid: false },
  { id: "invalid-negative-protein", override: { protein: "-0.01" }, valid: false },
  { id: "invalid-negative-fat", override: { fat: "-0.01" }, valid: false },
  { id: "invalid-negative-carbs", override: { carbs: "-0.01" }, valid: false },
] as const;

export const dishBoundaryCases = [
  { id: "invalid-portion-zero", portionSize: "0", quantity: "100", valid: false },
  { id: "valid-portion-001", portionSize: "0.01", quantity: "0.01", valid: true },
  { id: "invalid-ingredient-zero", portionSize: "250", quantity: "0", valid: false },
  { id: "valid-ingredient-001", portionSize: "250", quantity: "0.01", valid: true },
  { id: "invalid-name-length-1", name: "A", portionSize: "250", quantity: "100", valid: false },
  { id: "invalid-blank-name", name: "    ", portionSize: "250", quantity: "100", valid: false },
  { id: "valid-name-length-2", name: "Ok", portionSize: "250", quantity: "100", valid: true },
  { id: "valid-macro-sum-equals-portion", portionSize: "100", quantity: "100", protein: "40", fat: "30", carbs: "30", valid: true },
  { id: "invalid-macro-sum-above-portion", portionSize: "100", quantity: "100", protein: "40", fat: "30", carbs: "30.01", valid: false },
  { id: "invalid-negative-calories", portionSize: "250", quantity: "100", calories: "-0.01", valid: false },
  { id: "invalid-negative-protein", portionSize: "250", quantity: "100", protein: "-0.01", valid: false },
  { id: "invalid-negative-fat", portionSize: "250", quantity: "100", fat: "-0.01", valid: false },
  { id: "invalid-negative-carbs", portionSize: "250", quantity: "100", carbs: "-0.01", valid: false },
] as const;

export const dishCategoryMacroCases = [
  { id: "dessert", macro: "!десерт", expectedCategory: "Десерт" },
  { id: "first", macro: "!первое", expectedCategory: "Первое" },
  { id: "second", macro: "!второе", expectedCategory: "Второе" },
  { id: "drink", macro: "!напиток", expectedCategory: "Напиток" },
  { id: "salad", macro: "!салат", expectedCategory: "Салат" },
  { id: "soup", macro: "!суп", expectedCategory: "Суп" },
  { id: "snack", macro: "!перекус", expectedCategory: "Перекус" },
] as const;
