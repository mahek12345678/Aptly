/**
 * CareerRoadIllustration
 *
 * Vector implementation of Image 2:
 * A winding career road with milestone pins, a businessman in suit running with briefcase,
 * and a golden trophy at the top destination.
 * Matches Image 2 exactly with clean vector graphics and soft background integration.
 */
export default function CareerRoadIllustration({
  className = '',
}: {
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 700 520"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Career roadmap illustration showing progression towards goals"
    >
      <defs>
        {/* Soft sky gradient */}
        <linearGradient id="skyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#D9EAF7" stopOpacity="0.85" />
          <stop offset="50%" stopColor="#CBE2F4" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#BBD8F0" stopOpacity="0.95" />
        </linearGradient>

        {/* Road Gradient */}
        <linearGradient id="roadGrad" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#252A34" />
          <stop offset="50%" stopColor="#2D3340" />
          <stop offset="100%" stopColor="#353C4B" />
        </linearGradient>

        {/* Trophy Gold Gradient */}
        <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FBD44C" />
          <stop offset="50%" stopColor="#F2BA22" />
          <stop offset="100%" stopColor="#D99B0F" />
        </linearGradient>

        {/* Pin Blue Gradient */}
        <linearGradient id="pinGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#3F85D8" />
          <stop offset="100%" stopColor="#1E5AA8" />
        </linearGradient>

        {/* Cloud glow / shadow */}
        <filter id="softGlow" x="-10%" y="-10%" width="120%" height="120%">
          <feDropShadow dx="0" dy="4" stdDeviation="6" floodColor="#90B8DE" floodOpacity="0.3" />
        </filter>
      </defs>

      {/* Decorative Clouds */}
      {/* Cloud 1 (Top Left) */}
      <g opacity="0.9" filter="url(#softGlow)">
        <path
          d="M130 145 C130 135, 140 125, 155 125 C160 115, 175 110, 190 115 C205 105, 225 112, 230 128 C240 128, 250 136, 250 145 C250 155, 240 160, 230 160 L145 160 C135 160, 130 155, 130 145 Z"
          fill="#FFFFFF"
        />
      </g>

      {/* Cloud 2 (Mid Right) */}
      <g opacity="0.85" filter="url(#softGlow)">
        <path
          d="M540 220 C540 212, 548 205, 560 205 C565 198, 578 194, 590 198 C602 190, 618 195, 622 208 C630 208, 638 215, 638 222 C638 230, 630 234, 622 234 L552 234 C544 234, 540 230, 540 220 Z"
          fill="#FFFFFF"
        />
      </g>

      {/* Cloud 3 (Bottom Center-Left) */}
      <g opacity="0.85" filter="url(#softGlow)">
        <path
          d="M190 320 C190 310, 200 302, 212 302 C218 292, 234 288, 248 294 C260 285, 280 290, 285 304 C296 304, 305 312, 305 322 C305 332, 295 338, 285 338 L205 338 C195 338, 190 330, 190 320 Z"
          fill="#FFFFFF"
        />
      </g>

      {/* ============================================================ */}
      {/* THE WINDING ROAD                                             */}
      {/* ============================================================ */}
      {/* Base Asphalt Road (Outer curve ribbon) */}
      <path
        d="M -30 540 
           C 120 480, 230 460, 280 430
           C 350 390, 370 330, 310 290
           C 250 250, 220 200, 300 160
           C 380 120, 480 140, 515 110
           L 535 118
           C 495 155, 385 140, 320 180
           C 255 220, 275 270, 345 310
           C 415 350, 395 420, 315 460
           C 245 495, 120 520, -15 580
           Z"
        fill="url(#roadGrad)"
      />

      {/* Main Smooth Road Body for cleaner rendering */}
      <path
        d="M -40 560
           C 130 500, 250 480, 300 445
           C 380 395, 390 315, 305 275
           C 235 235, 235 175, 325 140
           C 410 105, 485 125, 520 110"
        stroke="#282E3B"
        strokeWidth="68"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />

      {/* Road inner edge / 3D rim highlight */}
      <path
        d="M -40 560
           C 130 500, 250 480, 300 445
           C 380 395, 390 315, 305 275
           C 235 235, 235 175, 325 140
           C 410 105, 485 125, 520 110"
        stroke="#363E4F"
        strokeWidth="62"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />

      {/* Road Dashed Centerlines */}
      <path
        d="M -40 560
           C 130 500, 250 480, 300 445
           C 380 395, 390 315, 305 275
           C 235 235, 235 175, 325 140
           C 410 105, 485 125, 520 110"
        stroke="#FFFFFF"
        strokeWidth="4.5"
        strokeDasharray="14 16"
        strokeLinecap="round"
        fill="none"
        opacity="0.9"
      />

      {/* ============================================================ */}
      {/* MILESTONE PINS (Image 2 style: Blue teardrop + white circle) */}
      {/* ============================================================ */}

      {/* Pin 1: Bottom Left */}
      <g transform="translate(110, 430)">
        <path
          d="M0 -34 C12 -34 20 -24 20 -12 C20 4 0 24 0 24 C0 24 -20 4 -20 -12 C-20 -24 -12 -34 0 -34 Z"
          fill="url(#pinGrad)"
        />
        <circle cx="0" cy="-14" r="8" fill="#FFFFFF" />
      </g>

      {/* Pin 2: Lower-Right Curve */}
      <g transform="translate(390, 380)">
        <path
          d="M0 -34 C12 -34 20 -24 20 -12 C20 4 0 24 0 24 C0 24 -20 4 -20 -12 C-20 -24 -12 -34 0 -34 Z"
          fill="url(#pinGrad)"
        />
        <circle cx="0" cy="-14" r="8" fill="#FFFFFF" />
      </g>

      {/* Pin 3: Middle-Left Curve */}
      <g transform="translate(250, 240)">
        <path
          d="M0 -34 C12 -34 20 -24 20 -12 C20 4 0 24 0 24 C0 24 -20 4 -20 -12 C-20 -24 -12 -34 0 -34 Z"
          fill="url(#pinGrad)"
        />
        <circle cx="0" cy="-14" r="8" fill="#FFFFFF" />
      </g>

      {/* Pin 4: Upper-Right Near Finish */}
      <g transform="translate(485, 175)">
        <path
          d="M0 -34 C12 -34 20 -24 20 -12 C20 4 0 24 0 24 C0 24 -20 4 -20 -12 C-20 -24 -12 -34 0 -34 Z"
          fill="url(#pinGrad)"
        />
        <circle cx="0" cy="-14" r="8" fill="#FFFFFF" />
      </g>

      {/* ============================================================ */}
      {/* RUNNING BUSINESSMAN (Blue suit, briefcase, tie)              */}
      {/* ============================================================ */}
      <g transform="translate(210, 280)">
        {/* Dynamic Running Shadow */}
        <ellipse cx="65" cy="85" rx="35" ry="7" fill="#1C222C" opacity="0.25" />

        {/* Trailing Blue Necktie */}
        <path
          d="M58 20 C42 16, 28 10, 18 12 C14 13, 10 18, 14 18 C26 18, 42 22, 54 26 Z"
          fill="#3B82F6"
        />

        {/* Back Leg (Left Leg) */}
        <path
          d="M48 48 L15 54 L-2 75 L10 77 L24 60 L50 52 Z"
          fill="#1C385E"
        />
        {/* Back Shoe */}
        <path d="M-5 74 L-15 75 L-12 83 L12 81 L10 76 Z" fill="#4B2818" />

        {/* Front Leg (Right Leg) */}
        <path
          d="M62 48 L88 70 L72 98 L85 101 L102 72 L72 45 Z"
          fill="#244978"
        />
        {/* Front Shoe */}
        <path d="M70 96 L66 106 L90 105 L88 98 Z" fill="#4B2818" />

        {/* Briefcase (held in left hand behind) */}
        <g transform="translate(-15, 30) rotate(-15)">
          {/* Briefcase Body */}
          <rect x="0" y="0" width="38" height="28" rx="4" fill="#8B4A28" />
          <rect x="0" y="8" width="38" height="12" fill="#783D1F" />
          {/* Handle */}
          <path d="M12 0 C12 -6, 26 -6, 26 0" stroke="#5A2C14" strokeWidth="3" fill="none" />
          {/* Brass Clasps */}
          <rect x="8" y="7" width="5" height="4" rx="1" fill="#F4C542" />
          <rect x="25" y="7" width="5" height="4" rx="1" fill="#F4C542" />
        </g>

        {/* Left Arm / Hand holding briefcase */}
        <path
          d="M52 24 L22 36 L12 44 L16 48 L28 40 L56 30 Z"
          fill="#1C385E"
        />
        {/* Left hand skin */}
        <circle cx="12" cy="46" r="4" fill="#E8B298" />

        {/* Suit Torso (leaning forward) */}
        <path
          d="M46 16 L74 24 L64 56 L44 50 Z"
          fill="#224977"
        />
        {/* White shirt collar & chest */}
        <path d="M58 18 L68 22 L62 36 L56 22 Z" fill="#FFFFFF" />
        {/* Front tie knot */}
        <path d="M60 20 L64 22 L62 32 L58 30 Z" fill="#2563EB" />

        {/* Right Arm (forward pump) */}
        <path
          d="M66 22 L92 28 L104 20 L108 24 L94 36 L68 28 Z"
          fill="#28548A"
        />
        {/* Right hand skin fist */}
        <circle cx="106" cy="21" r="5" fill="#E8B298" />

        {/* Head & Neck */}
        <path d="M56 12 L64 14 L62 20 L54 18 Z" fill="#E8B298" />
        {/* Face Profile */}
        <path
          d="M60 4 C68 4 72 8 72 14 C72 17 68 19 62 19 C56 19 55 13 55 10 C55 6 57 4 60 4 Z"
          fill="#E8B298"
        />
        {/* Hair (Slick/styled brown hair blowing in wind) */}
        <path
          d="M53 8 C50 4, 56 -1, 65 0 C72 1, 74 6, 73 10 C70 9, 66 8, 64 6 C60 7, 56 6, 53 8 Z"
          fill="#3E2419"
        />
      </g>

      {/* ============================================================ */}
      {/* FINISH PLATFORM & GOLDEN TROPHY                              */}
      {/* ============================================================ */}
      <g transform="translate(505, 65)">
        {/* Finish Platform Base */}
        <rect x="0" y="44" width="46" height="8" rx="2" fill="#7A4222" />
        <rect x="4" y="40" width="38" height="5" fill="#995830" />

        {/* Trophy Body */}
        {/* Trophy Cup */}
        <path
          d="M10 2 C10 2, 8 26, 23 26 C38 26, 36 2, 36 2 Z"
          fill="url(#goldGrad)"
          stroke="#D4960D"
          strokeWidth="1.5"
        />
        {/* Trophy Rim */}
        <ellipse cx="23" cy="2" rx="13" ry="2.5" fill="#FEE066" stroke="#D4960D" strokeWidth="1" />

        {/* Left Handle */}
        <path
          d="M10 6 C2 6, 2 18, 12 18"
          stroke="#D4960D"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
        />
        {/* Right Handle */}
        <path
          d="M36 6 C44 6, 44 18, 34 18"
          stroke="#D4960D"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
        />

        {/* Trophy Stem & Pedestal */}
        <path d="M20 26 L26 26 L25 36 L21 36 Z" fill="#D99B0F" />
        <rect x="15" y="35" width="16" height="5" rx="1.5" fill="#F2BA22" stroke="#D4960D" strokeWidth="1" />
      </g>
    </svg>
  );
}
