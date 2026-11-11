/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export type ToolCategory = "dishes" | "linen" | "appliance" | "utensils" | "tableware" | "cutlery";
export type DishShape = "rectangular" | "round";
export type DishUsage = "induction" | "gas" | "oven" | "microwave";
export type ExportTypes = "json";
export type IngredientFoodNutritionSource = "ciqual" | "usda" | "off" | "ai";
export type IngredientFoodNutritionLogOrigin = "estimate" | "fill";
export type IngredientFoodNutritionLogStepKind =
  "batch" | "single" | "retry" | "lookup" | "open_food_facts" | "usda" | "match";
export type RegisteredParser = "nlp" | "brute" | "openai";
export type OrderByNullPosition = "first" | "last";
export type OrderDirection = "asc" | "desc";
export type TimelineEventType = "system" | "info" | "comment";
export type TimelineEventImage = "has image" | "does not have image";
export type ThermomixLogStatus = "success" | "error";

export interface AssignCategories {
  recipes: string[];
  categories: CategoryDraft[];
}
export interface CategoryDraft {
  id?: string | null;
  groupId?: string | null;
  name: string;
  slug?: string | null;
  recipeCount?: number;
}
export interface AssignSettings {
  recipes: string[];
  settings: RecipeSettings;
}
export interface RecipeSettings {
  public?: boolean;
  showNutrition?: boolean;
  showAssets?: boolean;
  showAllergens?: boolean;
  landscapeView?: boolean;
  disableComments?: boolean;
  locked?: boolean;
  thermomix?: boolean;
}
export interface AssignTags {
  recipes: string[];
  tags: TagDraft[];
}
export interface TagDraft {
  id?: string | null;
  groupId?: string | null;
  name: string;
  slug?: string | null;
  recipeCount?: number;
}
export interface CategoryCreate {
  name: string;
}
export interface CategoryOut {
  id: string;
  groupId: string;
  name: string;
  slug: string;
  recipeCount: number;
}
export interface CategorySave {
  name: string;
  groupId: string;
}
export interface CategoryWithRecipes {
  id: string;
  groupId: string;
  name: string;
  slug: string;
  recipeCount: number;
  recipes: RecipeSummary[];
}
export interface RecipeSummary {
  id: string;
  userId: string;
  householdId: string;
  groupId: string;
  name: string;
  slug: string;
  image: string | null;
  recipeServings: number;
  recipeYieldQuantity: number;
  recipeYield: string | null;
  totalTime: string | null;
  prepTime: string | null;
  performTime: string | null;
  coolingTime: string | null;
  restTime: string | null;
  totalTimeSeconds: number | null;
  prepTimeSeconds: number | null;
  performTimeSeconds: number | null;
  coolingTimeSeconds: number | null;
  restTimeSeconds: number | null;
  description: string | null;
  recipeCategory: CategoryOut[];
  tags: TagOut[];
  tools: ToolOut[];
  rating: number | null;
  orgURL: string | null;
  dateAdded: string | null;
  dateUpdated: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}
export interface TagOut {
  id: string;
  groupId: string;
  name: string;
  slug: string;
  recipeCount: number;
}
export interface ToolOut {
  id: string;
  groupId: string;
  name: string;
  slug: string;
  recipeCount: number;
  householdsWithTool: string[];
  category: ToolCategory;
  image: string | null;
  dishShape: DishShape | null;
  length: number | null;
  width: number | null;
  height: number | null;
  diameter: number | null;
  usages: DishUsage[];
  parentId: string | null;
}
export interface DeleteRecipes {
  recipes: string[];
}
export interface ExportBase {
  recipes: string[];
}
export interface ExportRecipes {
  recipes: string[];
  exportType?: ExportTypes;
}
export interface IngredientConfidence {
  average?: number | null;
  comment?: number | null;
  name?: number | null;
  unit?: number | null;
  quantity?: number | null;
  food?: number | null;
}
export interface IngredientFoodAlias {
  name: string;
}
export interface IngredientFoodAliasCreate {
  name: string;
}
export interface IngredientFoodAllergenFillRequest {
  foodIds?: string[] | null;
  overwrite?: boolean;
}
export interface IngredientFoodAllergenSuggestRequest {
  name: string;
  pluralName?: string | null;
  aliases?: string[];
  description?: string | null;
}
export interface IngredientFoodCreate {
  id?: string | null;
  name: string;
  pluralName?: string | null;
  description?: string;
  extras?: {
    [k: string]: unknown;
  } | null;
  labelId?: string | null;
  aliases?: IngredientFoodAliasCreate[];
  substitutions?: IngredientFoodSubstitutionCreate[];
  householdsWithIngredientFood?: string[];
  allergens?: AllergenSummary[];
  nutrition?: Nutrition | null;
  averageWeight?: number | null;
  nutritionSource?: IngredientFoodNutritionSource | null;
  nutritionReferenceCode?: string | null;
  nutritionReferenceName?: string | null;
}
export interface IngredientFoodSubstitutionCreate {
  substituteFoodId?: string | null;
  additionalFoodIds?: string[];
  note?: string | null;
}
export interface AllergenSummary {
  id: string;
  name: string;
  code: string | null;
}
export interface Nutrition {
  calories?: string | null;
  carbohydrateContent?: string | null;
  cholesterolContent?: string | null;
  fatContent?: string | null;
  fiberContent?: string | null;
  proteinContent?: string | null;
  saturatedFatContent?: string | null;
  sodiumContent?: string | null;
  sugarContent?: string | null;
  transFatContent?: string | null;
  unsaturatedFatContent?: string | null;
  calciumContent?: string | null;
  ironContent?: string | null;
  magnesiumContent?: string | null;
  potassiumContent?: string | null;
  vitaminAContent?: string | null;
  vitaminCContent?: string | null;
  vitaminDContent?: string | null;
}
export interface IngredientFoodMerge {
  fromFood: string;
  toFood: string;
}
export interface IngredientFoodNutritionEstimate {
  nutrition: Nutrition;
  averageWeight: number | null;
  source: IngredientFoodNutritionSource | null;
  referenceCode: string | null;
  referenceName: string | null;
}
export interface IngredientFoodNutritionEstimateItem {
  id?: string | null;
  name: string;
  pluralName?: string | null;
  description?: string | null;
}
export interface IngredientFoodNutritionEstimateRequest {
  foods: [IngredientFoodNutritionEstimateItem, ...IngredientFoodNutritionEstimateItem[]];
}
export interface IngredientFoodNutritionFillRequest {
  foodIds: [string, ...string[]];
  overwrite?: boolean;
}
export interface IngredientFoodNutritionIssue {
  code: string;
  params?: {
    [k: string]: string | number;
  };
}
export interface IngredientFoodNutritionLogCorrection {
  field: string;
  before?: number | null;
  after?: number | null;
}
export interface IngredientFoodNutritionLogOut {
  groupId: string;
  foodId: string;
  origin: IngredientFoodNutritionLogOrigin;
  aiModel: string | null;
  steps: IngredientFoodNutritionLogStep[];
  corrections: IngredientFoodNutritionLogCorrection[];
  result: IngredientFoodNutritionEstimate | null;
  error: string | null;
  id: string;
  createdAt: string | null;
}
export interface IngredientFoodNutritionLogStep {
  kind: IngredientFoodNutritionLogStepKind;
  foodsCount?: number;
  response?: {
    [k: string]: unknown;
  } | null;
  issues?: IngredientFoodNutritionIssue[];
  error?: string | null;
  kept?: boolean;
}
export interface IngredientFoodNutritionLogSave {
  groupId: string;
  foodId: string;
  origin: IngredientFoodNutritionLogOrigin;
  aiModel?: string | null;
  steps?: IngredientFoodNutritionLogStep[];
  corrections?: IngredientFoodNutritionLogCorrection[];
  result?: IngredientFoodNutritionEstimate | null;
  error?: string | null;
}
export interface IngredientFoodNutritionReference {
  source: IngredientFoodNutritionSource;
  code: string;
  name: string;
  nutrition: Nutrition;
  averageWeight: number | null;
}
export interface IngredientFoodOut {
  id: string;
  name: string;
  pluralName: string | null;
  description: string;
  extras: {
    [k: string]: unknown;
  } | null;
  labelId: string | null;
  aliases: IngredientFoodAlias[];
  substitutions: IngredientFoodSubstitution[];
  householdsWithIngredientFood: string[];
  allergens: AllergenSummary[];
  nutrition: Nutrition | null;
  averageWeight: number | null;
  nutritionSource: IngredientFoodNutritionSource | null;
  nutritionReferenceCode: string | null;
  nutritionReferenceName: string | null;
  label: MultiPurposeLabelSummary | null;
  recipeCount: number;
  createdAt: string | null;
  updatedAt: string | null;
}
export interface IngredientFoodSubstitution {
  substituteFoodId?: string | null;
  additionalFoodIds?: string[];
  note?: string | null;
  substituteFood?: IngredientFoodSummary | null;
  additionalFoods?: IngredientFoodSummary[];
}
export interface IngredientFoodSummary {
  id: string;
  name: string;
  pluralName: string | null;
}
export interface MultiPurposeLabelSummary {
  name: string;
  color: string;
  groupId: string;
  id: string;
}
export interface IngredientFoodSave {
  id?: string | null;
  name: string;
  pluralName?: string | null;
  description?: string;
  extras?: {
    [k: string]: unknown;
  } | null;
  labelId?: string | null;
  aliases?: IngredientFoodAliasCreate[];
  substitutions?: IngredientFoodSubstitutionCreate[];
  householdsWithIngredientFood?: string[];
  allergens?: AllergenSummary[];
  nutrition?: Nutrition | null;
  averageWeight?: number | null;
  nutritionSource?: IngredientFoodNutritionSource | null;
  nutritionReferenceCode?: string | null;
  nutritionReferenceName?: string | null;
  groupId: string;
}
export interface IngredientReferences {
  referenceId?: string | null;
}
export interface IngredientRequest {
  parser?: RegisteredParser;
  ingredient: string;
}
export interface IngredientUnitAlias {
  name: string;
}
export interface IngredientUnitAliasCreate {
  name: string;
}
export interface IngredientUnitCreate {
  id?: string | null;
  name: string;
  pluralName?: string | null;
  description?: string;
  extras?: {
    [k: string]: unknown;
  } | null;
  fraction?: boolean;
  abbreviation?: string;
  pluralAbbreviation?: string | null;
  useAbbreviation?: boolean;
  aliases?: IngredientUnitAliasCreate[];
  standardQuantity?: number | null;
  standardUnit?: string | null;
}
export interface IngredientUnitMerge {
  fromUnit: string;
  toUnit: string;
}
export interface IngredientUnitOut {
  id: string;
  name: string;
  pluralName: string | null;
  description: string;
  extras: {
    [k: string]: unknown;
  } | null;
  fraction: boolean;
  abbreviation: string;
  pluralAbbreviation: string | null;
  useAbbreviation: boolean;
  aliases: IngredientUnitAlias[];
  standardQuantity: number | null;
  standardUnit: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}
export interface IngredientUnitSave {
  id?: string | null;
  name: string;
  pluralName?: string | null;
  description?: string;
  extras?: {
    [k: string]: unknown;
  } | null;
  fraction?: boolean;
  abbreviation?: string;
  pluralAbbreviation?: string | null;
  useAbbreviation?: boolean;
  aliases?: IngredientUnitAliasCreate[];
  standardQuantity?: number | null;
  standardUnit?: string | null;
  groupId: string;
}
export interface IngredientsRequest {
  parser?: RegisteredParser;
  ingredients: string[];
}
export interface NoteReference {
  referenceId?: string | null;
}
export interface OrganizerDraft {
  id?: string | null;
  groupId?: string | null;
  name: string;
  slug?: string | null;
  recipeCount?: number;
}
export interface OrganizerMerge {
  fromId: string;
  toId: string;
}
export interface OrganizerOut {
  id: string;
  groupId: string;
  name: string;
  slug: string;
  recipeCount: number;
}
export interface ParsedIngredient {
  input?: string | null;
  confidence?: IngredientConfidence;
  ingredient: RecipeIngredient;
}
export interface RecipeIngredient {
  quantity?: number | null;
  unit?: IngredientUnitOut | IngredientUnitCreate | null;
  food?: IngredientFoodOut | IngredientFoodCreate | null;
  referencedRecipe?: RecipeDraft | null;
  note?: string | null;
  display?: string;
  title?: string | null;
  originalText?: string | null;
  substitutions?: RecipeIngredientSubstitution[];
  referenceId?: string;
}
export interface RecipeDraft {
  id?: string | null;
  userId?: string | null;
  householdId?: string | null;
  groupId?: string | null;
  name?: string | null;
  slug?: string;
  image?: unknown;
  recipeServings?: number;
  recipeYieldQuantity?: number;
  recipeYield?: string | null;
  totalTime?: string | null;
  prepTime?: string | null;
  performTime?: string | null;
  coolingTime?: string | null;
  restTime?: string | null;
  totalTimeSeconds?: number | null;
  prepTimeSeconds?: number | null;
  performTimeSeconds?: number | null;
  coolingTimeSeconds?: number | null;
  restTimeSeconds?: number | null;
  description?: string | null;
  recipeCategory?: CategoryDraft[];
  tags?: TagDraft[];
  tools?: ToolDraft[];
  rating?: number | null;
  orgURL?: string | null;
  dateAdded?: string | null;
  dateUpdated?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  recipeIngredient?: RecipeIngredient[];
  recipeInstructions?: RecipeStep[];
  nutrition?: Nutrition | null;
  settings?: RecipeSettings | null;
  assets?: RecipeAsset[];
  notes?: RecipeNote[];
  extras?: {
    [k: string]: unknown;
  };
  comments?: RecipeCommentOut[];
}
export interface ToolDraft {
  id?: string | null;
  groupId?: string | null;
  name: string;
  slug?: string | null;
  recipeCount?: number;
  householdsWithTool?: string[];
}
export interface RecipeStep {
  id?: string | null;
  title?: string | null;
  summary?: string | null;
  text: string;
  ingredientReferences?: IngredientReferences[];
  noteReferences?: NoteReference[];
  toolReferences?: ToolReference[];
  stepReferences?: StepReference[];
  durationSeconds?: number | null;
  coolingSeconds?: number | null;
  cookingSeconds?: number | null;
  restSeconds?: number | null;
}
export interface ToolReference {
  referenceId?: string | null;
}
export interface StepReference {
  referenceId?: string | null;
}
export interface RecipeAsset {
  name: string;
  icon: string;
  fileName?: string | null;
}
export interface RecipeNote {
  title: string;
  text: string;
  referenceId?: string;
}
export interface RecipeCommentOut {
  id: string;
  recipeId: string;
  text: string;
  createdAt: string;
  updatedAt: string;
  userId: string;
  user: RecipeCommentUser;
}
export interface RecipeCommentUser {
  id: string;
  username?: string | null;
  admin: boolean;
  fullName?: string | null;
}
export interface RecipeIngredientSubstitution {
  substituteFoodId?: string | null;
  additionalFoodIds?: string[];
  note?: string | null;
  substituteFood?: IngredientFoodSummary | null;
  additionalFoods?: IngredientFoodSummary[];
}
export interface RecipeCommentCreate {
  recipeId: string;
  text: string;
}
export interface RecipeCommentSave {
  recipeId: string;
  text: string;
  userId: string;
}
export interface RecipeCommentUpdate {
  id: string;
  text: string;
}
export interface RecipeCreate {
  name: string;
  thermomix?: boolean;
}
export interface RecipeDuplicate {
  name?: string | null;
}
export interface RecipeIngredientBase {
  quantity?: number | null;
  unit?: IngredientUnitOut | IngredientUnitCreate | null;
  food?: IngredientFoodOut | IngredientFoodCreate | null;
  referencedRecipe?: RecipeDraft | null;
  note?: string | null;
  display?: string;
}
export interface RecipeIngredientSubstitutionCreate {
  substituteFoodId?: string | null;
  additionalFoodIds?: string[];
  note?: string | null;
}
export interface RecipeLastMade {
  timestamp: string;
}
export interface RecipeOut {
  id: string;
  userId: string;
  householdId: string;
  groupId: string;
  name: string;
  slug: string;
  image: string | null;
  recipeServings: number;
  recipeYieldQuantity: number;
  recipeYield: string | null;
  totalTime: string | null;
  prepTime: string | null;
  performTime: string | null;
  coolingTime: string | null;
  restTime: string | null;
  totalTimeSeconds: number | null;
  prepTimeSeconds: number | null;
  performTimeSeconds: number | null;
  coolingTimeSeconds: number | null;
  restTimeSeconds: number | null;
  description: string | null;
  recipeCategory: CategoryOut[];
  tags: TagOut[];
  tools: ToolOut[];
  rating: number | null;
  orgURL: string | null;
  dateAdded: string | null;
  dateUpdated: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  recipeIngredient: RecipeIngredient[];
  recipeInstructions: RecipeStep[];
  nutrition: Nutrition;
  settings: RecipeSettings;
  assets: RecipeAsset[];
  notes: RecipeNote[];
  extras: {
    [k: string]: unknown;
  };
  comments: RecipeCommentOut[];
}
export interface RecipeShareTokenCreate {
  recipeId: string;
  expiresAt?: string;
}
export interface RecipeShareTokenOut {
  recipeId: string;
  expiresAt: string;
  groupId: string;
  id: string;
  createdAt: string;
  recipe: RecipeOut;
}
export interface RecipeShareTokenSave {
  recipeId: string;
  expiresAt?: string;
  groupId: string;
}
export interface RecipeShareTokenSummary {
  recipeId: string;
  expiresAt: string;
  groupId: string;
  id: string;
  createdAt: string;
}
export interface RecipeSuggestionQuery {
  orderBy?: string | null;
  orderByNullPosition?: OrderByNullPosition | null;
  orderDirection?: OrderDirection;
  queryFilter?: string | null;
  paginationSeed?: string | null;
  limit?: number;
  maxMissingFoods?: number;
  maxMissingTools?: number;
  includeFoodsOnHand?: boolean;
  includeToolsOnHand?: boolean;
  includeSubstitutions?: boolean;
}
export interface RecipeSuggestionResponse {
  items: RecipeSuggestionResponseItem[];
}
export interface RecipeSuggestionResponseItem {
  recipe: RecipeSummary;
  missingFoods: IngredientFoodOut[];
  substitutedFoods: RecipeSuggestionSubstitutedFood[];
  missingTools: ToolOut[];
}
export interface RecipeSuggestionSubstitutedFood {
  food: IngredientFoodOut;
  substituteFood: IngredientFoodSummary;
}
export interface RecipeThermomixView {
  steps: ThermomixStep[];
  notes: string[];
  model: string | null;
  createdAt: string;
}
export interface ThermomixStep {
  id?: string;
  title?: string | null;
  summary?: string | null;
  text: string;
  timeSeconds?: number | null;
  coolingSeconds?: number | null;
  cookingSeconds?: number | null;
  restSeconds?: number | null;
  temperature?: string | null;
  speed?: string | null;
  reverse?: boolean;
  accessory?: string | null;
  sourceStepIds?: string[];
  toolIds?: string[];
  cautions?: string[];
}
export interface RecipeTimelineEventCreate {
  recipeId: string;
  userId: string;
  subject: string;
  eventType: TimelineEventType;
  eventMessage?: string | null;
  image?: TimelineEventImage | null;
  timestamp?: string;
}
export interface RecipeTimelineEventIn {
  recipeId: string;
  userId?: string | null;
  subject: string;
  eventType: TimelineEventType;
  eventMessage?: string | null;
  image?: TimelineEventImage | null;
  timestamp?: string;
}
export interface RecipeTimelineEventOut {
  recipeId: string;
  userId: string;
  subject: string;
  eventType: TimelineEventType;
  eventMessage: string | null;
  image: TimelineEventImage | null;
  timestamp: string;
  id: string;
  groupId: string;
  householdId: string;
  createdAt: string;
  updatedAt: string;
}
export interface RecipeTimelineEventUpdate {
  subject: string;
  eventMessage?: string | null;
  image?: TimelineEventImage | null;
}
export interface RecipeUrlBulkCreate {
  imports: RecipeUrlCreate[];
}
export interface RecipeUrlCreate {
  url: string;
  categories?: CategoryDraft[] | null;
  tags?: TagDraft[] | null;
}
export interface ScrapeRecipe {
  includeTags?: boolean;
  includeCategories?: boolean;
  url: string;
}
export interface ScrapeRecipeAI {
  content?: string | null;
  url?: string | null;
  translateLanguage?: string | null;
  createNewOrganizers?: boolean;
}
export interface ScrapeRecipeBase {
  includeTags?: boolean;
  includeCategories?: boolean;
}
export interface ScrapeRecipeData {
  includeTags?: boolean;
  includeCategories?: boolean;
  data: string;
  url?: string | null;
}
export interface ScrapeRecipeTest {
  url: string;
  useOpenAI?: boolean;
}
export interface SubstitutionBase {
  substituteFoodId?: string | null;
  additionalFoodIds?: string[];
  note?: string | null;
}
export interface TagCreate {
  name: string;
}
export interface TagSave {
  name: string;
  groupId: string;
}
export interface TagWithRecipes {
  id: string;
  groupId: string;
  name: string;
  slug: string;
  recipeCount: number;
  recipes: RecipeSummary[];
}
export interface ThermomixLogEntry {
  id: string;
  createdAt: string;
  status: ThermomixLogStatus;
  user: string | null;
  provider: string | null;
  model: string | null;
  timeoutSeconds: number | null;
  durationMs: number;
  promptChars: number;
  estimatedTokens: number;
  request: string;
  response: {
    [k: string]: unknown;
  } | null;
  stepsCount: number;
  error: string | null;
}
export interface ToolCreate {
  name: string;
  householdsWithTool?: string[];
  category?: ToolCategory;
  dishShape?: DishShape | null;
  length?: number | null;
  width?: number | null;
  height?: number | null;
  diameter?: number | null;
  usages?: DishUsage[];
  parentId?: string | null;
}
export interface ToolSave {
  name: string;
  householdsWithTool?: string[];
  category?: ToolCategory;
  dishShape?: DishShape | null;
  length?: number | null;
  width?: number | null;
  height?: number | null;
  diameter?: number | null;
  usages?: DishUsage[];
  parentId?: string | null;
  groupId: string;
}
export interface ToolWithRecipes {
  id: string;
  groupId: string;
  name: string;
  slug: string;
  recipeCount: number;
  householdsWithTool: string[];
  category: ToolCategory;
  image: string | null;
  dishShape: DishShape | null;
  length: number | null;
  width: number | null;
  height: number | null;
  diameter: number | null;
  usages: DishUsage[];
  parentId: string | null;
  recipes: RecipeSummary[];
}
export interface UnitFoodBase {
  id?: string | null;
  name: string;
  pluralName?: string | null;
  description?: string;
  extras?: {
    [k: string]: unknown;
  } | null;
}
export interface UpdateImageResponse {
  image: string;
}
export interface MealieOutModel {}
export interface RequestQuery {
  orderBy?: string | null;
  orderByNullPosition?: OrderByNullPosition | null;
  orderDirection?: OrderDirection;
  queryFilter?: string | null;
  paginationSeed?: string | null;
}
