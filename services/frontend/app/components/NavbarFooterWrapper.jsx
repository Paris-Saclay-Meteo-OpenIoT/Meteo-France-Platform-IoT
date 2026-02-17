"use client";
import { useSelectedLayoutSegments } from "next/navigation";
import Navbar from "./navbar";
import Footer from "./Footer";

export default function NavbarFooterWrapper({ children }) {

    const segments = useSelectedLayoutSegments();
    const isDashboard = segments[0] === "dashboard_admin";

    return (
        <>
            {!isDashboard && <Navbar />}
            {children}
            {!isDashboard && <Footer />}
        </>
    );
}