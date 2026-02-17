"use client";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    if (!email || !password) {
      setError("Veuillez remplir tous les champs.");
      return;
    }

    const res = await login(email, password);
    if (!res.success) {
      setError(res.error || "Identifiants incorrects");
    } else {
      router.push("/");
    }
  }

  return (
    <div className="flex justify-center items-center h-screen">
      <form onSubmit={handleLogin} className="bg-white p-6 rounded shadow-md">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Connexion</h2>
        <input
          type="email"
          placeholder="Email"
          className="border p-2 w-full text-gray-700 mb-2"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          placeholder="Mot de passe"
          className="border p-2 w-full text-gray-700 mb-2"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="text-red-500 text-sm mt-2">{error}</p>} 
        <div className="flex justify-between items-center w-full">
          <button type="submit" className="bg-blue-500 text-white px-4 py-2 rounded">Se connecter</button>
          <button type="button" onClick={() => window.location.href = `/register`} className="text-blue-600 hover:underline">S'inscrire</button>
        </div>
      </form>
    </div>
  );
}