'use client';
import Link from "next/link";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const isAdmin = user?.role === "admin";
  
  return (
    <nav className="bg-blue-600 text-white px-6 py-4 flex justify-between items-center shadow-md">
      <div className="flex space-x-6">
        <Link href="/" className="hover:underline">Accueil</Link>
        <Link href="/map" className="hover:underline">Carte</Link>
        <Link href="/forecast" className="hover:underline">Prévisions</Link>
        {user ? (
          <>
            {isAdmin && <Link href="/dashboard_admin" className="hover:underline">Admin</Link>}
          </>
        ) : null}
      </div>
      {user ? (
        <>
          <span className="text-sm">Bonjour, {user.prenom} 👋</span>
          <button
            onClick={logout}
            className="bg-red-500 px-4 py-2 rounded-md hover:bg-red-700 transition"
          >
            Déconnexion
          </button>
        </>
      ) : (
        <Link href="/login" className="bg-blue-900 px-4 py-2 rounded-md hover:bg-blue-700 transition">
          Connexion
        </Link>
      )}
    </nav>
  );
}