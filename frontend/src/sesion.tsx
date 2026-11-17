import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { api, getToken, setToken, type Rol } from "./api";

// El JWT de Auth trae sub y rol. Aquí solo se LEE para pintar la interfaz; quien decide si
// el token es válido es cada microservicio (firma ES256, emisor, audiencia, expiración).
interface Usuario { id: string; rol: Rol; email: string }

function leerToken(t: string | null, email = localStorage.getItem("email") ?? ""): Usuario | null {
  if (!t) return null;
  try {
    const datos = JSON.parse(atob(t.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    if (datos.exp * 1000 < Date.now()) return null;
    return { id: datos.sub, rol: datos.rol, email };
  } catch {
    return null;
  }
}

interface Sesion {
  usuario: Usuario | null;
  entrar: (email: string, clave: string) => Promise<Usuario>;
  salir: () => void;
}

const Contexto = createContext<Sesion | null>(null);

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(() => leerToken(getToken()));
  const valor = useMemo<Sesion>(() => ({
    usuario,
    entrar: async (email, clave) => {
      const r = await api<{ access_token: string }>("/api/v1/auth/sesiones", {
        method: "POST", body: { email, password: clave },
      });
      setToken(r.access_token);
      localStorage.setItem("email", email);
      const u = leerToken(r.access_token, email)!;
      setUsuario(u);
      return u;
    },
    salir: () => {
      setToken(null);
      localStorage.removeItem("email");
      setUsuario(null);
    },
  }), [usuario]);
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSesion(): Sesion {
  const s = useContext(Contexto);
  if (!s) throw new Error("useSesion fuera del proveedor");
  return s;
}
