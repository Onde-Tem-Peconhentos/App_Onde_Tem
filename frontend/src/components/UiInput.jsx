import React from "react";
import styles from "./styles/UiInput.module.css";

export default function UiInput({
  name,
  value,
  onChange,
  placeholder = "",
  type = "text",
  disabled = false,
  autoComplete,
}) {
  return (
    <div className={styles.wrapper}>
      <input
        className={styles.input}
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        type={type}
        disabled={disabled}
        autoComplete={autoComplete}
      />
    </div>
  );
}
