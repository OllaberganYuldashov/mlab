import { type FormEvent, useState } from "react";
import { api, fieldErrors } from "../api";
import { t } from "../i18n";

export default function ChangePasswordPage({
  forced,
  onChanged,
}: {
  forced: boolean;
  onChanged: () => void;
}) {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setErrors({});
    setFormError(null);
    try {
      const result = await api("/api/auth/change-password", {
        method: "POST",
        body: { old_password: oldPassword, new_password: newPassword },
      });
      if (result.ok) {
        setDone(true);
        setOldPassword("");
        setNewPassword("");
        onChanged();
      } else if (result.status === 400) {
        const found = fieldErrors(result.data);
        setErrors(found);
        if (Object.keys(found).length === 0) setFormError(t("common.unexpectedError"));
      } else {
        setFormError(t("common.unexpectedError"));
      }
    } catch {
      setFormError(t("common.networkError"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app">
      <h1>{t("password.title")}</h1>
      {forced && <p role="status">{t("password.required")}</p>}
      {done && <p role="status">{t("password.success")}</p>}
      <form onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="old_password">{t("field.oldPassword")}</label>
          <input
            id="old_password"
            name="old_password"
            type="password"
            autoComplete="current-password"
            required
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            aria-invalid={errors.old_password ? true : undefined}
          />
          {errors.old_password && <p className="error">{errors.old_password}</p>}
        </div>
        <div className="field">
          <label htmlFor="new_password">{t("field.newPassword")}</label>
          <input
            id="new_password"
            name="new_password"
            type="password"
            autoComplete="new-password"
            required
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            aria-invalid={errors.new_password ? true : undefined}
          />
          {errors.new_password && <p className="error">{errors.new_password}</p>}
        </div>
        {formError && (
          <p role="alert" className="error">
            {formError}
          </p>
        )}
        <button type="submit" disabled={busy}>
          {t("password.submit")}
        </button>
      </form>
    </main>
  );
}
