import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom"; 
import HomePage from "./pages/HomePage";
import BuscaPage from "./pages/BuscaPage";
import DashboardPage from "./pages/DashboardPage";
import SobrePage from "./pages/SobrePage";
import NossoTime from "./pages/NossoTimePage";
import ScrollToTop from "./components/ScrollToTop";
import Modelos from "./pages/Modelos"

export default function App() {
  return (
    <Router>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/busca" element={<BuscaPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/modelos" element={<Modelos />} />
        <Route path="/sobre" element={<SobrePage />} />
        <Route path="/nosso-time" element={<NossoTime />} />
      </Routes>
    </Router>
  );
}
