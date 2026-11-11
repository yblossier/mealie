/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export interface OpenAICompiledSource {
  contains_recipe: boolean;
  content: string;
  language?: string | null;
  image_url?: string | null;
}
export interface OpenAIFoodAllergens {
  name: string;
  allergens?: string[];
}
export interface OpenAIFoodNutrition {
  name?: string | null;
  calories?: number | null;
  carbohydrate_content?: number | null;
  cholesterol_content?: number | null;
  fat_content?: number | null;
  fiber_content?: number | null;
  protein_content?: number | null;
  saturated_fat_content?: number | null;
  sodium_content?: number | null;
  sugar_content?: number | null;
  trans_fat_content?: number | null;
  unsaturated_fat_content?: number | null;
  calcium_content?: number | null;
  iron_content?: number | null;
  magnesium_content?: number | null;
  potassium_content?: number | null;
  vitamin_a_content?: number | null;
  vitamin_c_content?: number | null;
  vitamin_d_content?: number | null;
  average_weight?: number | null;
}
export interface OpenAIFoodNutritionMatch {
  name?: string | null;
  reference?: string | null;
  average_weight?: number | null;
}
export interface OpenAIFoodNutritionMatches {
  foods?: OpenAIFoodNutritionMatch[];
}
export interface OpenAIFoodsAllergens {
  foods?: OpenAIFoodAllergens[];
}
export interface OpenAIFoodsNutrition {
  foods?: OpenAIFoodNutrition[];
}
export interface OpenAIIngredient {
  quantity?: number | null;
  unit?: string | null;
  food?: string | null;
  note?: string | null;
  substitutes?: string[];
}
export interface OpenAIIngredients {
  ingredients?: OpenAIIngredient[];
}
export interface OpenAIInstructionEnrichment {
  step: number;
  ingredients?: number[];
  notes?: number[];
  duration?: string | null;
  summary?: string | null;
  text?: string | null;
}
export interface OpenAIInstructionEnrichments {
  instructions?: OpenAIInstructionEnrichment[];
}
export interface OpenAIOrganizers {
  tags?: string[];
  categories?: string[];
  tools?: string[];
}
export interface OpenAIRecipe {
  name: string;
  description?: string | null;
  recipe_yield?: string | null;
  total_time?: string | null;
  prep_time?: string | null;
  perform_time?: string | null;
  ingredients?: OpenAIRecipeIngredient[];
  instructions?: OpenAIRecipeInstruction[];
  notes?: OpenAIRecipeNotes[];
  nutrition?: OpenAIRecipeNutrition | null;
}
export interface OpenAIRecipeIngredient {
  title?: string | null;
  text: string;
}
export interface OpenAIRecipeInstruction {
  title?: string | null;
  text: string;
}
export interface OpenAIRecipeNotes {
  title?: string | null;
  text: string;
}
export interface OpenAIRecipeNutrition {
  calories?: string | null;
  carbohydrate_content?: string | null;
  cholesterol_content?: string | null;
  fat_content?: string | null;
  fiber_content?: string | null;
  protein_content?: string | null;
  saturated_fat_content?: string | null;
  sodium_content?: string | null;
  sugar_content?: string | null;
  trans_fat_content?: string | null;
  unsaturated_fat_content?: string | null;
}
export interface OpenAIText {
  text: string;
}
export interface OpenAIThermomixStep {
  title?: string | null;
  text: string;
  time_seconds?: number | null;
  cooking_seconds?: number | null;
  rest_seconds?: number | null;
  cooling_seconds?: number | null;
  temperature?: string | null;
  speed?: string | null;
  reverse?: boolean | null;
  accessory?: string | null;
  source_steps?: number[];
  tools?: string[];
  cautions?: string[];
}
export interface OpenAIThermomixView {
  steps?: OpenAIThermomixStep[];
  notes?: string[];
}
export interface OpenAIBase {}
