// Fotos reales de Santa Marta (Wikimedia Commons, licencias libres; créditos en /creditos).
// Van empaquetadas en /public/fotos para que la PWA las muestre también sin conexión.
// Si Catálogo trae imágenes propias de la oferta (imagen_oferta), esas tienen prioridad.
import creditos from "./fotos-creditos.json";

export type ClaveFoto = keyof typeof creditos;
export const foto = (c: ClaveFoto) => `/fotos/${c}.webp`;

export interface Credito { archivo: string; autor: string; licencia: string; url_licencia: string; pagina: string }
export const CREDITOS = creditos as Record<ClaveFoto, Credito>;

/** Foto de cada zona (por el código de Catálogo). */
export const FOTO_ZONA: Record<string, ClaveFoto> = {
  tayrona: "tayrona",
  minca: "minca",
  taganga: "taganga",
  centro: "catedral",
  "los-naranjos": "naranjos",
  rodadero: "rodadero",
};

/** Texto corto de cada zona para la franja de destinos. */
export const LEMA_ZONA: Record<string, [string, string]> = {
  tayrona: ["Playas vírgenes y selva tropical", "Pristine beaches and rainforest"],
  minca: ["Cascadas, café y aves en la Sierra", "Waterfalls, coffee and birds"],
  taganga: ["Pueblo de pescadores y arrecifes", "Fishing village and reefs"],
  centro: ["La ciudad más antigua de Colombia", "Colombia's oldest city"],
  "los-naranjos": ["Senderos donde el río llega al mar", "Trails where the river meets the sea"],
  rodadero: ["Playa urbana y atardeceres", "City beach and sunsets"],
};

// Por nombre de la experiencia primero (más preciso), luego por categoría.
const POR_NOMBRE: [RegExp, ClaveFoto[]][] = [
  [/minca|cascada|waterfall/i, ["minca-cascada", "sierra", "minca"]],
  [/pueblito|chairama/i, ["pueblito", "pueblito-terrazas"]],
  [/cristal/i, ["playa-cristal", "tayrona"]],
  [/cocina|gastronom|cooking|comida/i, ["cocina", "taganga"]],
  [/museo|oro|gold|hist[oó]ric|catedral/i, ["catedral", "oro", "aduana"]],
  [/buceo|scuba|diving|snorkel/i, ["buceo", "taganga"]],
  [/naranjos/i, ["naranjos", "tayrona-costa"]],
  [/rodadero/i, ["rodadero", "atardecer"]],
  [/tayrona|cabo san juan/i, ["tayrona", "tayrona-costa"]],
];
const POR_CATEGORIA: Record<string, ClaveFoto> = {
  playa: "playa-cristal", naturaleza: "minca", cultura: "aduana", historia: "catedral", gastronomia: "cocina", aventura: "buceo",
};

/** Fotos de una oferta: imágenes del catálogo si existen; si no, las de la experiencia, su zona o su categoría. */
export function fotosDeOferta(
  o: { nombre_es: string; atributos?: { categorias?: string[] } },
  zonaCodigo?: string,
  imagenesCatalogo: { clave_objeto: string }[] = [],
): string[] {
  const propias = imagenesCatalogo.map((i) => i.clave_objeto).filter((u) => /^(https?:)?\//.test(u));
  if (propias.length) return propias;
  const porNombre = POR_NOMBRE.find(([re]) => re.test(o.nombre_es))?.[1];
  const claves: ClaveFoto[] = [...(porNombre ?? [])];
  if (zonaCodigo && FOTO_ZONA[zonaCodigo]) claves.push(FOTO_ZONA[zonaCodigo]);
  const cat = o.atributos?.categorias?.[0];
  if (cat && POR_CATEGORIA[cat]) claves.push(POR_CATEGORIA[cat]);
  if (claves.length === 0) claves.push("heroe");
  return [...new Set(claves)].map(foto);
}
