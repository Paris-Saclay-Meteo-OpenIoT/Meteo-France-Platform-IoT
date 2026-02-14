"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../context/AuthContext";

export default function RegisterPage() {
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [nom, setLastname] = useState("");
  const [prenom, setFirstname] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  function isPasswordValid(password) {
    const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
    return regex.test(password);
  }

  async function handleRegister(e) {
    e.preventDefault();
    setError("");
    if (!isPasswordValid(password)) {
      setError("Le mot de passe doit contenir au moins 8 caractères, une majuscule, une minuscule et un chiffre.");
      return; // Bloque l'envoi de la requête
    }
  
    console.log("Données envoyées :", { email, nom, prenom, password });
    const res = await register(email, nom, prenom, password);
    if (!res.success) {
      setError("Un utilisateur avec cet email existe déjà");
    } else {
      router.push("/");
    }
  }

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md mt-10">
      <h2 className="text-2xl font-bold text-gray-900 text-center mb-4">Inscription</h2>
      <form onSubmit={handleRegister} className="space-y-4">
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full text-gray-700 p-2 border rounded"
        />
        <input
          type="text"
          placeholder="Nom"
          value={nom}
          onChange={(e) => setLastname(e.target.value)}
          required
          className="w-full text-gray-700 p-2 border rounded"
        />
        <input
          type="text"
          placeholder="Prénom"
          value={prenom}
          onChange={(e) => setFirstname(e.target.value)}
          required
          className="w-full text-gray-700 p-2 border rounded"
        />
        <input
          type="password"
          placeholder="Mot de passe"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full text-gray-700 p-2 border rounded"
        />

        {error && (
          <p className="text-red-500 text-sm mt-2">{error}</p>
        )}

        <div className="flex justify-between items-center w-full">
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">S'inscrire</button>
          <button type="button" onClick={() => window.location.href = `/login`} className="text-blue-600 hover:underline">Déjà un compte ?</button>
        </div>
      </form>
    </div>
  );
}