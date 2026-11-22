/**
 * Interfeys matnlari (NFR-14). Hamma ko'rinadigan matn faqat shu yerdan olinadi.
 * R3 da rus tili qo'shilganda ru.json va til tanlash qo'shiladi; chaqiruvchi kod o'zgarmaydi.
 */
import uz from "./uz.json";

export type MessageKey = keyof typeof uz;

const messages: Record<string, string> = uz;

export function t(key: MessageKey, params: Record<string, string | number> = {}): string {
  const template = messages[key];
  if (template === undefined) {
    throw new Error(`Tarjima kaliti topilmadi: ${key}`);
  }
  return template.replace(/\{(\w+)\}/g, (match: string, name: string) =>
    name in params ? String(params[name]) : match,
  );
}
