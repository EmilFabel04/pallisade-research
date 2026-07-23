export function SharePointIcon({ size = 20, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
      <circle cx="10.3" cy="7" r="5.6" fill="#036c70" />
      <circle cx="15.2" cy="12.2" r="5" fill="#1a9ba1" />
      <circle cx="11" cy="17.4" r="4.2" fill="#37c6d0" />
      <path fill="#fff" d="M8.7 6.1H6.1v6.3h1.4v-2.2h1a2 2 0 1 0 .2-4.1zm-.2 3H7.5V7.3h1a.9.9 0 0 1 0 1.8z" />
    </svg>
  );
}
