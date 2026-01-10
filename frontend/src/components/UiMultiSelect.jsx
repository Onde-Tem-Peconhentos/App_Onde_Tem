import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import uiSelectStyles from "./styles/UiSelect.module.css";
import styles from "./styles/UiMultiSelect.module.css";

function ChevronIcon({ className }) {
  return (
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
}

function CheckIcon({ className }) {
  return (
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
}

/**
 * UiMultiSelect
 * - values: array de values selecionados
 * - onChange: igual UiSelect -> onChange({ target: { name, value: array } })
 * - options: [{ label, value }]
 */
export default function UiMultiSelect({
  label,
  name,
  values = [],
  onChange,
  options = [],
  placeholder = "Selecione.",
  disabled = false,

  // extras
  showSelectAll = true, // mostra opção "Todos"
  selectAllLabel = "Todos",
  closeOnSelect = false, // em multi select normalmente fica aberto
  maxChips = 3, // quantos chips mostrar antes de virar "+N"
}) {
  const id = useId();
  const wrapperRef = useRef(null);
  const safeValues = Array.isArray(values) ? values : [];

  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);

  const selectedOptions = useMemo(() => {
    const set = new Set(safeValues);
    return options.filter((o) => set.has(o.value));
  }, [options, safeValues]);

  const selectedIndex = useMemo(() => {
    if (safeValues.length === 0) return -1;
    const set = new Set(safeValues);
    return options.findIndex((o) => set.has(o.value));
  }, [options, safeValues]);

  useEffect(() => {
    if (open) setHighlight(selectedIndex >= 0 ? selectedIndex : 0);
  }, [open, selectedIndex]);

  useEffect(() => {
    const onDocClick = (e) => {
      if (!wrapperRef.current) return;
      if (!wrapperRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const emit = (nextValues) => {
    onChange?.({ target: { name, value: nextValues } });
  };

  const clearAll = () => {
    emit([]);
    setOpen(false);
  };

  const toggleValue = (val) => {
    const has = safeValues.includes(val);
    const next = has
      ? safeValues.filter((v) => v !== val)
      : [...safeValues, val];
    emit(next);
    if (closeOnSelect) setOpen(false);
  };

  const removeChip = (val, e) => {
    e.stopPropagation();
    emit(safeValues.filter((v) => v !== val));
  };

  const onKeyDown = (e) => {
    if (disabled) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        if (!open) return setOpen(true);
        setHighlight((i) => Math.min(i + 1, options.length - 1));
        break;

      case "ArrowUp":
        e.preventDefault();
        if (!open) return setOpen(true);
        setHighlight((i) => Math.max(i - 1, 0));
        break;

      case "Enter":
      case " ":
        e.preventDefault();
        if (!open) return setOpen(true);
        if (options[highlight]) toggleValue(options[highlight].value);
        break;

      case "Escape":
        setOpen(false);
        break;

      case "Home":
        if (open) setHighlight(0);
        break;

      case "End":
        if (open) setHighlight(options.length - 1);
        break;

      case "Tab":
        setOpen(false);
        break;

      default:
        break;
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
        className={`${uiSelectStyles.control} ${
          open ? uiSelectStyles.open : ""
        } ${disabled ? uiSelectStyles.disabled : ""}`}
        role="combobox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        aria-labelledby={`${id}-label`}
        tabIndex={disabled ? -1 : 0}
        onClick={() => !disabled && setOpen((v) => !v)}
        onKeyDown={onKeyDown}
      >
        <div
          className={
            safeValues.length > 0
              ? `${uiSelectStyles.valueText} ${styles.valueTextMulti}`
              : `${uiSelectStyles.valueText} ${uiSelectStyles.placeholder}`
          }
        >
          {safeValues.length === 0 ? (
            placeholder
          ) : (
            <div className={styles.chips}>
              {selectedOptions.slice(0, maxChips).map((opt) => (
                <span key={opt.value} className={styles.chip}>
                  <span className={styles.chipText}>{opt.label}</span>
                  <button
                    type="button"
                    className={styles.chipRemove}
                    onClick={(e) => removeChip(opt.value, e)}
                    aria-label={`Remover ${opt.label}`}
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
        </div>

        <ChevronIcon className={uiSelectStyles.chevron} />
      </div>

      {open && (
        <ul
          id={`${id}-list`}
          role="listbox"
          aria-labelledby={`${id}-label`}
          aria-multiselectable="true"
          className={uiSelectStyles.menu}
        >
          {showSelectAll && (
            <li
              role="option"
              aria-selected={safeValues.length === 0}
              className={`${uiSelectStyles.option} ${
                safeValues.length === 0 ? uiSelectStyles.optionSelected : ""
              }`}
              onClick={clearAll}
            >
              <span className={uiSelectStyles.optionLabel}>
                {selectAllLabel}
              </span>
              {safeValues.length === 0 && (
                <CheckIcon className={uiSelectStyles.check} />
              )}
            </li>
          )}

          {options.map((opt, i) => {
            const isSelected = safeValues.includes(opt.value);
            const isActive = i === highlight;

            return (
              <li
                key={opt.value}
                role="option"
                aria-selected={isSelected}
                className={`${uiSelectStyles.option} ${
                  isSelected ? uiSelectStyles.optionSelected : ""
                } ${isActive ? uiSelectStyles.optionActive : ""}`}
                onMouseEnter={() => setHighlight(i)}
                onClick={() => toggleValue(opt.value)}
              >
                <span className={uiSelectStyles.optionLabel}>{opt.label}</span>
                {isSelected && <CheckIcon className={uiSelectStyles.check} />}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
