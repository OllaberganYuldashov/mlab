/** Qo'shilish havolasi uchun QR (ADR-0005: qrcode-generator). SVG `data:` URL — innerHTML ishlatilmaydi. */
import qrcode from "qrcode-generator";

export function qrDataUrl(text: string): string {
  const qr = qrcode(0, "M");
  qr.addData(text);
  qr.make();
  const svg = qr.createSvgTag({ cellSize: 6, margin: 2, scalable: true });
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}
