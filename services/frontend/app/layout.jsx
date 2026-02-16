import "./globals.css";
import NavbarFooterWrapper from "./components/NavbarFooterWrapper";
import { ToastContainer } from "react-toastify"; 
import "react-toastify/dist/ReactToastify.css";
import { AuthProvider } from "./context/AuthContext";

export default function RootLayout({ children }) {
  return (
    <html lang="fr">
      <head>
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        />
        <script
          src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
          defer
        ></script>
      </head>
      <body className="flex flex-col min-h-screen">
        <AuthProvider>
          <NavbarFooterWrapper>
            <main className="flex-1 flex items-center justify-center">
              {children}
            </main>
          </NavbarFooterWrapper>
          <ToastContainer /> 
        </AuthProvider>
      </body>
    </html>
  );
}
