export function OneDriveIcon({ size = 20, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
      <path fill="#0364b8" d="M13.5 9.5 9.7 6.2A5.6 5.6 0 0 0 3 9.9a4.6 4.6 0 0 0 .4 9.1h4.1z" />
      <path fill="#0078d4" d="M14.4 9.2a5 5 0 0 0-4.7-3l-.5 3.3 4.3 3.7 2.6-.6z" />
      <path fill="#1490df" d="M20 12.6a4 4 0 0 0-3.4-2 3.9 3.9 0 0 0-.5 0l-2.6 2.4-2.3 2.9 9.9.1a4 4 0 0 0-1.1-3.4z" />
      <path fill="#28a8ea" d="M7.6 19h12.3a4 4 0 0 0 1.2-.2l-8.4-5.9-8 3.6A4.6 4.6 0 0 0 7.6 19z" />
    </svg>
  );
}
