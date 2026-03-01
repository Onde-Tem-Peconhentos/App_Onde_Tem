import React, { useEffect, useMemo, useRef, useState, useId } from "react";
import uiSelectStyles from "./styles/UiSelect.module.css";
import styles from "./styles/UiMultiSelect.module.css";

// --- Sub-componentes Visuais (Icons) ---
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

export default function UiMultiSelect({
  label,
  name,
  values = [],
  onChange,
  options = [],
  placeholder = "Selecione.",
  disabled = false,
  searchable = true,
  showSelectAll = true,
  selectAllLabel = "Todos",
  closeOnSelect = false,
  maxChips = 3,
}) {
  const id = useId();
  const wrapperRef = useRef(null);
  const inputRef = useRef(null);

  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [query, setQuery] = useState("");

  const safeValues = useMemo(
    () => (Array.isArray(values) ? values : []),
    [values]
  );

  // --- Lógica de Seleção e Filtro ---
  const selectedOptions = useMemo(() => {
    const set = new Set(safeValues);
    return options.filter((o) => set.has(o.value));
  }, [options, safeValues]);

  const filteredOptions = useMemo(() => {
    if (!searchable || !open || !query.trim()) return options;
    const q = query.trim().toLowerCase();
    return options.filter((o) => String(o.label).toLowerCase().includes(q));
  }, [options, query, searchable, open]);

  const items = useMemo(() => {
    const list = [];
    if (showSelectAll) list.push({ type: "all" });
    filteredOptions.forEach((opt) => list.push({ type: "opt", opt }));
    return list;
  }, [filteredOptions, showSelectAll]);

  // --- Handlers de Ação ---
  const emit = (nextValues) => {
    onChange?.({ target: { name, value: nextValues } });
    if (closeOnSelect) setOpen(false);
  };

  const toggleValue = (val) => {
    const next = safeValues.includes(val)
      ? safeValues.filter((v) => v !== val)
      : [...safeValues, val];
    emit(next);
  };

  const removeChip = (val, e) => {
    e.stopPropagation();
    emit(safeValues.filter((v) => v !== val));
  };

  const clearAll = () => emit([]);

  const activateHighlighted = () => {
    const item = items[highlight];
    if (!item) return;
    item.type === "all" ? clearAll() : toggleValue(item.opt.value);
  };

  // --- Efeitos de UI ---
  useEffect(() => {
    const onDocClick = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target))
        setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setHighlight(0);
    if (searchable) setTimeout(() => inputRef.current?.focus(), 0);
  }, [open, searchable]);

  useEffect(() => {
    if (open) setHighlight((h) => Math.max(0, Math.min(h, items.length - 1)));
  }, [open, items.length]);

  // --- Acessibilidade (Teclado) ---
  const onKeyDown = (e) => {
    if (disabled) return;
    const actions = {
      ArrowDown: () =>
        open
          ? setHighlight((i) => Math.min(i + 1, items.length - 1))
          : setOpen(true),
      ArrowUp: () =>
        open ? setHighlight((i) => Math.max(i - 1, 0)) : setOpen(true),
      Enter: () => (open ? activateHighlighted() : setOpen(true)),
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

  return (
    <div className={uiSelectStyles.wrapper} ref={wrapperRef}>
      {label && (
        <label className={uiSelectStyles.label} id={`${id}-label`}>
          {label}
        </label>
      )}

      <div
        className={`${uiSelectStyles.control} ${open ? uiSelectStyles.open : ""} ${disabled ? uiSelectStyles.disabled : ""}`}
        role="combobox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        aria-labelledby={`${id}-label`}
        onMouseDown={(e) => {
          if (disabled) return;
          e.preventDefault();
          setOpen(true);
        }}
      >
        <div
          className={`${uiSelectStyles.valueText} ${styles.valueTextMulti} ${styles.inlineField}`}
          onKeyDown={onKeyDown}
        >
          {/* Renderização de Chips */}
          {safeValues.length > 0 && (
            <div className={styles.chips}>
              {selectedOptions.slice(0, maxChips).map((opt) => (
                <span key={opt.value} className={styles.chip}>
                  <span className={styles.chipText}>{opt.label}</span>
                  <button
                    type="button"
                    className={styles.chipRemove}
                    onClick={(e) => removeChip(opt.value, e)}
                  >
                    ×
                  </button>
                </span>
              ))}
              {selectedOptions.length > maxChips && (
                <span className={styles.more}>
                  +{selectedOptions.length - maxChips}
                </span>
              )}
            </div>
          )}

          {/* Campo de Busca ou Placeholder */}
          {searchable ? (
            <input
              ref={inputRef}
              className={styles.searchInline}
              value={open ? query : ""}
              placeholder={safeValues.length === 0 ? placeholder : ""}
              readOnly={!open}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              onMouseDown={(e) => e.stopPropagation()}
              disabled={disabled}
            />
          ) : (
            safeValues.length === 0 && (
              <span className={uiSelectStyles.placeholder}>{placeholder}</span>
            )
          )}
        </div>
        <ChevronIcon className={uiSelectStyles.chevron} />
      </div>

      {/* Menu de Opções */}
      {open && (
        <ul
          id={`${id}-list`}
          role="listbox"
          aria-multiselectable="true"
          className={uiSelectStyles.menu}
          onMouseDown={(e) => e.preventDefault()}
        >
          {showSelectAll && (
            <li
              role="option"
              aria-selected={safeValues.length === 0}
              className={`${uiSelectStyles.option} ${safeValues.length === 0 ? uiSelectStyles.optionSelected : ""} ${highlight === 0 ? uiSelectStyles.optionActive : ""}`}
              onMouseEnter={() => setHighlight(0)}
              onMouseDown={clearAll}
            >
              <span className={uiSelectStyles.optionLabel}>
                {selectAllLabel}
              </span>
              {safeValues.length === 0 && (
                <CheckIcon className={uiSelectStyles.check} />
              )}
            </li>
          )}

          {filteredOptions.length === 0 ? (
            <li className={uiSelectStyles.option} aria-disabled="true">
              <span className={uiSelectStyles.optionLabel}>
                Nenhum resultado
              </span>
            </li>
          ) : (
            filteredOptions.map((opt, i) => {
              const rowIndex = showSelectAll ? i + 1 : i;
              const isSelected = safeValues.includes(opt.value);
              return (
                <li
                  key={opt.value}
                  role="option"
                  aria-selected={isSelected}
                  className={`${uiSelectStyles.option} ${isSelected ? uiSelectStyles.optionSelected : ""} ${rowIndex === highlight ? uiSelectStyles.optionActive : ""}`}
                  onMouseEnter={() => setHighlight(rowIndex)}
                  onMouseDown={() => toggleValue(opt.value)}
                >
                  <span className={uiSelectStyles.optionLabel}>
                    {opt.label}
                  </span>
                  {isSelected && <CheckIcon className={uiSelectStyles.check} />}
                </li>
              );
            })
          )}
        </ul>
      )}
    </div>
  );
}
