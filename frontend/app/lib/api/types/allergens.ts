/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export interface AllergenCreate {
  name: string;
  code?: string | null;
  keywords?: string;
  exclusions?: string;
}
export interface AllergenOut {
  name: string;
  code: string | null;
  keywords: string;
  exclusions: string;
  groupId: string;
  id: string;
}
export interface AllergenSave {
  name: string;
  code?: string | null;
  keywords?: string;
  exclusions?: string;
  groupId: string;
}
export interface AllergenSummary {
  id: string;
  name: string;
  code: string | null;
}
export interface AllergenUpdate {
  name: string;
  code?: string | null;
  keywords?: string;
  exclusions?: string;
  groupId: string;
  id: string;
}
export interface RecipeAllergen {
  allergenId: string;
  code: string | null;
  name: string;
  ingredients: string[];
}
export interface MealieOutModel {}
