/** Vaqtlar Asia/Tashkent'da ko'rsatiladi (SRS); server ISO (offset bilan) qaytaradi. */
const FORMAT = new Intl.DateTimeFormat("uz-UZ", {
  timeZone: "Asia/Tashkent",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export function showTime(iso: string | null): string {
  return iso ? FORMAT.format(new Date(iso)) : "—";
}

/** `<input type="datetime-local">` qiymati (brauzer vaqti) → ISO; bo'sh — null. */
export function localToIso(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}
