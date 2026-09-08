interface PeloSiMarkProps {
  size?: number;
  className?: string;
}

// The ToTheMoon brand mark — an original caricature (not traced from any reference image)
// of a suited, sunglassed, blonde-haired figure riding a tilted rocket, one arm raised.
// Satirical in the same spirit as the site's name; a fresh illustration, not a copy of
// any existing artwork. This is the one component in the app whose colors are NOT
// Ledger tokens — see DESIGN.md's "brand mark" note for why that's a deliberate,
// scoped exception rather than drift. Shapes are kept bold/simple on purpose so the
// same mark reads clearly both tiny (the header, ~16-18px) and large (the homepage hero).
export default function PeloSiMark({ size = 16, className }: PeloSiMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="-15 -10 130 120"
      aria-hidden="true"
      className={className}
    >
      <g transform="rotate(28 50 50)">
        {/* flame */}
        <polygon points="44,66 50,88 56,66" fill="#f57c00" />
        <polygon points="46.5,66 50,79 53.5,66" fill="#ffd54f" />
        {/* fins */}
        <polygon points="40,52 25,69 40,69" fill="#c62828" />
        <polygon points="60,52 75,69 60,69" fill="#c62828" />
        {/* rocket body */}
        <rect x="38" y="24" width="24" height="42" rx="10" fill="#f5f5f0" stroke="#1c2b45" strokeWidth="1.5" />
        <circle cx="50" cy="40" r="7" fill="#2a5ca8" />
        <circle cx="50" cy="40" r="5" fill="#bcd9f7" />
        {/* nose cone */}
        <polygon points="50,6 61,26 39,26" fill="#c62828" />
        {/* figure: legs wrapping the body */}
        <g stroke="#1c2b45" strokeWidth="6" strokeLinecap="round" fill="none">
          <line x1="50" y1="34" x2="40" y2="47" />
          <line x1="50" y1="34" x2="60" y2="47" />
        </g>
        {/* arm gripping the rocket */}
        <line x1="46" y1="22" x2="38" y2="31" stroke="#1c2b45" strokeWidth="5" strokeLinecap="round" />
        {/* arm raised, pointing up */}
        <line x1="54" y1="20" x2="67" y2="5" stroke="#1c2b45" strokeWidth="5" strokeLinecap="round" />
        <circle cx="67" cy="5" r="3" fill="#e0a878" />
        {/* torso */}
        <rect x="43" y="19" width="14" height="17" rx="4" fill="#1c2b45" />
        <rect x="48.5" y="19" width="3" height="11" fill="#f5f5f0" />
        <polygon points="48.5,19 51.5,19 50,23" fill="#c62828" />
        {/* head + hair + sunglasses */}
        <circle cx="50" cy="12" r="8" fill="#e0a878" />
        <ellipse cx="50" cy="7" rx="9" ry="6" fill="#e8c460" />
        <rect x="43.5" y="11" width="13" height="4" rx="2" fill="#111111" />
      </g>
    </svg>
  );
}
