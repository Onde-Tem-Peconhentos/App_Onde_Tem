import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import styles from "./styles/UiSelect.module.css";

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

export default function UiSelect({
  label,
  name,
  value,
  onChange,
  options = [],
  placeholder = "Selecione...",
  disabled = false,
}) {
  const id = useId();
  const wrapperRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);

  const selectedIndex = useMemo(
    () => options.findIndex((o) => o.value === value),
    [options, value]
  );

  const selectedLabel = useMemo(
    () => (selectedIndex >= 0 ? options[selectedIndex].label : ""),
    [options, selectedIndex]
  );

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

  const commitChange = (val) => {
    onChange?.({ target: { name, value: val } });
    setOpen(false);
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
        e.preventDefault();
        if (!open) return setOpen(true);
        commitChange(options[highlight]?.value);
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
    <div className={styles.wrapper} ref={wrapperRef}>
      {label && (
        <label className={styles.label} id={`${id}-label`}>
          {label}
        </label>
      )}

      <div
        className={`${styles.control} ${open ? styles.open : ""} ${
          disabled ? styles.disabled : ""
        }`}
        role="combobox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        aria-labelledby={`${id}-label`}
        tabIndex={disabled ? -1 : 0}
        onClick={() => !disabled && setOpen((v) => !v)}
        onKeyDown={onKeyDown}
      >
        <span
          className={
            value
              ? styles.valueText
              : `${styles.valueText} ${styles.placeholder}`
          }
        >
          {value ? selectedLabel : placeholder}
        </span>
        <ChevronIcon className={styles.chevron} />
      </div>

      {open && (
        <ul
          id={`${id}-list`}
          role="listbox"
          aria-labelledby={`${id}-label`}
          className={styles.menu}
        >
          {options.map((opt, i) => {
            const isSelected = value === opt.value;
            const isActive = i === highlight;
            return (
              <li
                key={opt.value}
                role="option"
                aria-selected={isSelected}
                className={`${styles.option} ${
                  isSelected ? styles.optionSelected : ""
                } ${isActive ? styles.optionActive : ""}`}
                onMouseEnter={() => setHighlight(i)}
                onClick={() => commitChange(opt.value)}
              >
                <span className={styles.optionLabel}>{opt.label}</span>
                {isSelected && <CheckIcon className={styles.check} />}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
