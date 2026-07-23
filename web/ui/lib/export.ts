const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export const researchPdfUrl = (conversationId: string) =>
  `${API_BASE}/api/export/research/${conversationId}`;

export const debatePdfUrl = (runId: string) =>
  `${API_BASE}/api/export/debate/${runId}`;

/** Open the export URL in a new tab. A top-level GET carries the SameSite=lax
 *  session cookie; the server's Content-Disposition sets the filename. */
export function openPdf(url: string): void {
  window.open(url, "_blank", "noopener");
}
