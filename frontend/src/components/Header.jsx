import { useState } from "react";
import { Menu, X } from "lucide-react";
import { Link, NavLink } from "react-router-dom";
import logo from "../assets/logo.svg";
import styles from "./styles/Header.module.css";

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false);

  const toggleMenu = () => setMenuOpen((v) => !v);
  const closeMenu = () => setMenuOpen(false);

  // classe base + ativa (funciona p/ desktop e mobile)
  const linkClass = ({ isActive }) =>
    [styles.link, isActive && styles.activeLink].filter(Boolean).join(" ");

  return (
    <header className={styles.header}>
      {/* LOGO */}
      <div className={styles.logoContainer}>
        <img src={logo} alt="Logo Onde Tem" className={styles.logo} />
        <span className={styles.logoText}>Onde Tem</span>
      </div>

      {/* MENU DESKTOP */}
      <nav className={styles.navDesktop}>
        <NavLink to="/" end className={linkClass}>
          Home
        </NavLink>
        <NavLink to="/busca" className={linkClass}>
          Busca
        </NavLink>
        <NavLink to="/modelos" className={linkClass}>
          Modelos
        </NavLink>
        <NavLink to="/dashboard" className={linkClass}>
          Dashboard
        </NavLink>
        <NavLink to="/sobre" className={linkClass}>
          Sobre
        </NavLink>
        <NavLink to="/nosso-time" className={linkClass}>
          Nosso Time
        </NavLink>
      </nav>

      {/* BOTÃO DESKTOP */}
      <a
        href="mailto:contato@seudominio.com?subject=Contato%20pelo%20site%20Onde%20Tem"
        className={`${styles.contactButton} ${styles.desktopButton}`}
      >
        Entre em contato
      </a>

      {/* BOTÃO HAMBÚRGUER (MOBILE) */}
      <button
        className={styles.hamburgerButton}
        onClick={toggleMenu}
        aria-label="Abrir menu"
      >
        {menuOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* MENU LATERAL MOBILE */}
      {menuOpen && (
        <div className={styles.overlay} onClick={closeMenu}>
          <div
            className={`${styles.navContainer} ${menuOpen ? styles.open : ""}`}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className={styles.closeButton}
              onClick={closeMenu}
              aria-label="Fechar menu"
            >
              <X size={24} />
            </button>

            <nav className={styles.navMobile}>
              <NavLink to="/" end className={linkClass} onClick={closeMenu}>
                Home
              </NavLink>
              <NavLink to="/busca" className={linkClass} onClick={closeMenu}>
                Busca
              </NavLink>
              <NavLink to="/modelos" className={linkClass} onClick={closeMenu}>
                Modelos
              </NavLink>
              <NavLink
                to="/dashboard"
                className={linkClass}
                onClick={closeMenu}
              >
                Dashboard
              </NavLink>
              <NavLink to="/sobre" className={linkClass} onClick={closeMenu}>
                Sobre
              </NavLink>
              <NavLink to="/time" className={linkClass} onClick={closeMenu}>
                Nosso Time
              </NavLink>

              {/* Botão dentro do menu mobile */}
              <a
                href="mailto:contato@seudominio.com?subject=Contato%20pelo%20site%20Onde%20Tem"
                className={`${styles.contactButton} ${styles.desktopButton}`}
              >
                Entre em contato
              </a>
            </nav>
          </div>
        </div>
      )}
    </header>
  );
}
