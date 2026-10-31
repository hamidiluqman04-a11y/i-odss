import { useEffect, useRef } from "react";
import Icon from "./Icons";

/**
 * The short answer at the top of an analysis page: one headline a seller can
 * act on, plus a plain-language sentence. Only built from values the API returned.
 */
export function Answer({ headline, children, label = "The short answer" }) {
  return (
    <section className="answer" aria-label={label}>
      <p className="eyebrow">{label}</p>
      <p className="answer-headline">{headline}</p>
      {children && <div className="answer-body">{children}</div>}
    </section>
  );
}

/** "How this was calculated": methods, accuracy and limits, one click away (for examiners). */
export function Method({ hint = "Method, assumptions and limits", children }) {
  return (
    <details className="method">
      <summary>
        <span>
          <span className="method-title">How this was calculated</span>
          <span className="method-hint">{hint}</span>
        </span>
        <span className="method-chevron"><Icon name="chevron" /></span>
      </summary>
      <div className="method-body">{children}</div>
    </details>
  );
}

/**
 * Native modal confirmation. Escape and the Cancel button both cancel; focus
 * goes to Cancel on open (the safe choice) and back to the trigger on close.
 */
export function ConfirmDialog({ open, title, children, confirmLabel, busyLabel, busy, onConfirm, onCancel }) {
  const ref = useRef(null);
  const cancelRef = useRef(null);
  const returnTo = useRef(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      returnTo.current = document.activeElement;
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
      cancelRef.current?.focus();
    } else if (!open && dialog.open) {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
      const target = returnTo.current;
      if (target && document.contains(target)) target.focus();
    }
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="dialog"
      aria-labelledby="confirm-title"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onCancel();
      }}
    >
      <h2 id="confirm-title">{title}</h2>
      <div className="secondary" style={{ marginTop: "var(--space-sm)" }}>{children}</div>
      <div className="dialog-actions">
        <button ref={cancelRef} type="button" className="btn btn-secondary" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button type="button" className="btn btn-danger-solid" onClick={onConfirm} disabled={busy}>
          {busy ? busyLabel : confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
