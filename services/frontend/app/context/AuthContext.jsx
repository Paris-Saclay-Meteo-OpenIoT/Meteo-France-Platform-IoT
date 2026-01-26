"use client";
import { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const router = useRouter();

  // Vérifier si un token est stocké et récupérer l'utilisateur
  useEffect(() => {
    const Storedtoken = sessionStorage.getItem("token");
    if (Storedtoken) {
      fetchUser(Storedtoken);
    }
  }, []);

  async function fetchUser(token) {
    try {
      const res = await fetch("http://localhost:5000/api/users", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        logout();
      }
    } catch (error) {
      console.error("Erreur récupération utilisateur :", error);
    }
  }

  async function login(email, password) {
    try {
      const res = await fetch("http://localhost:5000/api/users/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const result = await res.json();
      console.log("Réponse API :", result);

      if (res.ok) {
        sessionStorage.setItem("token", result.token);
        setUser(result.user);
        return { success: true, user: result.user };
      } else {
        return { success: false, error: result.error || "Erreur de connexion." };
      }
    } catch (error) {
      console.error("Erreur de connexion :", error);
      return { success: false, error: "Erreur de communication avec le serveur." };
    }
  }

  async function register(email, nom, prenom, password) {
    try {
      const res = await fetch("http://localhost:5000/api/users/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, nom, prenom, password }),
      });

      const result = await res.json();
      console.log("Réponse API :", result);

      if (res.ok) {
        sessionStorage.setItem("token", result.token);
        setUser(result.user);
        alert("Inscription réussie !");
        return { success: true, user: result.user };
      } else {
        const errorMessages = {};
        if (result.errors) {
          result.errors.forEach((err) => {
          errorMessages[err.path] = err.msg;
          });
        }
        return { success: false, errors: errorMessages };
      }
    } catch (error) {
      console.error("Erreur de requête :", error);
      return { success: false, errors: { general: "Erreur de communication avec le serveur." } };
    }
  }

  function logout() {
    sessionStorage.removeItem("token");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}