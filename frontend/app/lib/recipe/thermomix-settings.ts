// Same settings chain as mealie/services/recipe/thermomix_settings.py, e.g. "5 min/100°C/sens inverse/vitesse 1"
const TIME = String.raw`\d+\s*(?:h|min|sec|s)\b(?:\s*\d+\s*(?:min|sec|s)\b)?`;
const TEMPERATURE = String.raw`(?:\d{2,3}\s*°\s*C?|varoma)`;
const SPEED_WORD = String.raw`(?:vitesse|speed|stufe|velocidad|velocità|vel\.?)`;
const SPEED = String.raw`(?:${SPEED_WORD}\s*(?:\d+(?:[.,]\d+)?|mijotage|cuill[eè]re|spoon|turbo)|turbo)`;
const REVERSE = String.raw`(?:sens\s+inverse|reverse|linkslauf|giro\s+(?:a\s+la\s+)?izquierda|antiorario)`;
const TOKEN = `(?:${TIME}|${TEMPERATURE}|${SPEED}|${REVERSE})`;
const CHAIN = new RegExp(`(\\*\\*)?(${TOKEN}(?:\\s*/\\s*${TOKEN})+)(\\*\\*)?`, "giu");

const TAG_CLASS = "thermomix-setting";

function formatSetting(setting: string): string {
  const value = setting.trim().replace(/\s+/g, " ");
  if (new RegExp(`^${TEMPERATURE}$`, "iu").test(value)) {
    return /varoma/i.test(value) ? "Varoma" : `${value.match(/\d+/)![0]}°C`;
  }
  if (new RegExp(`^${SPEED}$`, "iu").test(value)) {
    const speed = value.replace(new RegExp(`^${SPEED_WORD}\\s*`, "iu"), "");
    return /^turbo$/i.test(speed) ? "Turbo" : `Vitesse ${speed.toLowerCase()}`;
  }
  return value;
}

/** Writes a chain of Thermomix settings the way Thermomix recipes print it, e.g. "5 min/100°C/Vitesse 1" */
export function formatThermomixSettings(chain: string): string {
  return chain.split("/").map(formatSetting).join("/");
}

/** Puts the Thermomix settings of a step in a tag, the way Thermomix recipes highlight them */
export function tagThermomixSettings(text: string): string {
  return text.replace(CHAIN, (_match: string, _open: string | undefined, chain: string) =>
    `<span class="${TAG_CLASS}">${formatThermomixSettings(chain)}</span>`,
  );
}

const THERMOMIX_SITES = ["cookomix.com"];

/** True when the URL is a recipe of a site whose recipes are written for the Thermomix, e.g. Cookomix */
export function isThermomixSiteUrl(url: string | null | undefined): boolean {
  if (!url) {
    return false;
  }
  try {
    const { protocol, hostname } = new URL(url.trim());
    if (protocol !== "http:" && protocol !== "https:") {
      return false;
    }
    const host = hostname.toLowerCase().replace(/^www\./, "");
    return THERMOMIX_SITES.includes(host);
  }
  catch {
    return false;
  }
}

/** True when the recipe is already written for the Thermomix, so its steps need no Thermomix view */
export function isThermomixRecipe(recipe: { orgURL?: string | null; settings?: { thermomix?: boolean } | null }): boolean {
  return !!recipe.settings?.thermomix || isThermomixSiteUrl(recipe.orgURL);
}
