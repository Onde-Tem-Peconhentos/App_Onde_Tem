import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import styles from "./styles/UiSelect.module.css";

// --- Ícones Internos ---
const ChevronIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
    <path
      d="M6 9l6 6 6-6"
      stroke="currentColor"
      strokeWidth="2"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const CheckIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
    <path
      d="M20 6L9 17l-5-5"
      stroke="currentColor"
      strokeWidth="2"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export default function UiSelect({
  label,
  name,
  value,
  onChange,
  options = [],
  placeholder = "Selecione...",
  disabled = false,
  searchable = true,
}) {
  const id = useId();
  const wrapperRef = useRef(null);
  const inputRef = useRef(null);

  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [query, setQuery] = useState("");

  // --- Lógica de Seleção e Filtro ---
  const selectedIndex = useMemo(
    () => options.findIndex((o) => o.value === value),
    [options, value]
  );
  const selectedLabel = useMemo(
    () => (selectedIndex >= 0 ? options[selectedIndex].label : ""),
    [options, selectedIndex]
  );

  const filteredOptions = useMemo(() => {
    if (!searchable || !open || !query.trim()) return options;
    const q = query.trim().toLowerCase();
    return options.filter((o) => String(o.label).toLowerCase().includes(q));
  }, [options, query, searchable, open]);

  // --- Handlers de Ação ---
  const commitChange = (val) => {
    onChange?.({ target: { name, value: val } });
    setOpen(false);
    setQuery("");
  };

  const handleControlClick = (e) => {
    if (disabled) return;
    e.preventDefault();
    setOpen(true);
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  // --- Acessibilidade (Teclado) ---
  const onKeyDown = (e) => {
    if (disabled) return;

    const actions = {
      ArrowDown: () =>
        open
          ? setHighlight((i) => Math.min(i + 1, filteredOptions.length - 1))
          : setOpen(true),
      ArrowUp: () =>
        open ? setHighlight((i) => Math.max(i - 1, 0)) : setOpen(true),
      Enter: () => {
        if (!open) return setOpen(true);
        if (filteredOptions.length > 0)
          commitChange(filteredOptions[highlight]?.value);
      },
      Escape: () => {
        setOpen(false);
        setQuery("");
      },
      Tab: () => setOpen(false),
    };

    if (actions[e.key]) {
      e.preventDefault();
      actions[e.key]();
    }
  };

  // --- Efeitos ---
  useEffect(() => {
    if (!open) return;
    setQuery("");
    setHighlight(selectedIndex >= 0 ? selectedIndex : 0);
    if (searchable) setTimeout(() => inputRef.current?.focus(), 0);
  }, [open, searchable, selectedIndex]);

  useEffect(() => {
    const onDocClick = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target))
        setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const inputValue = open && searchable ? query : value ? selectedLabel : "";

  return (
    <div className={styles.wrapper} ref={wrapperRef}>
      {label && (
        <label className={styles.label} id={`${id}-label`}>
          {label}
        </label>
      )}

      <div
        className={`${styles.control} ${open ? styles.open : ""} ${disabled ? styles.disabled : ""}`}
        role="combobox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        aria-labelledby={`${id}-label`}
        onMouseDown={handleControlClick}
      >
        <input
          ref={inputRef}
          className={`${styles.valueText} ${!value && !(open && query) ? styles.placeholder : ""} ${styles.inputField}`}
          value={inputValue}
          placeholder={placeholder}
          disabled={disabled}
          readOnly={!open || !searchable}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <ChevronIcon className={styles.chevron} />
      </div>

      {open && (
        <ul
          id={`${id}-list`}
          role="listbox"
          className={styles.menu}
          onMouseDown={(e) => e.preventDefault()}
        >
          {filteredOptions.length === 0 ? (
            <li className={styles.empty}>Nenhum resultado</li>
          ) : (
            filteredOptions.map((opt, i) => {
              const isSelected = value === opt.value;
              const isActive = i === highlight;
              return (
                <li
                  key={opt.value}
                  role="option"
                  aria-selected={isSelected}
                  className={`${styles.option} ${isSelected ? styles.optionSelected : ""} ${isActive ? styles.optionActive : ""}`}
                  onMouseEnter={() => setHighlight(i)}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    commitChange(opt.value);
                  }}
                >
                  <span className={styles.optionLabel}>{opt.label}</span>
                  {isSelected && <CheckIcon className={styles.check} />}
                </li>
              );
            })
          )}
        </ul>
      )}
    </div>
  );
}
