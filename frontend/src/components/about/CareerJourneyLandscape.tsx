export const CareerJourneyLandscape: React.FC = () => {
  return (
    <div className="relative w-full max-w-[620px] mx-auto flex items-center justify-center select-none">
      <svg
        viewBox="0 0 640 370"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-auto object-contain"
        aria-label="A calm visual representation of the career journey showing Plan, Apply, and Grow markers"
      >
        <defs>
          {/* Subtle warm sun gradient */}
          <radialGradient id="sunGradient" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#FDE6D2" stopOpacity="0.85" />
            <stop offset="45%" stopColor="#FEEDDC" stopOpacity="0.5" />
            <stop offset="80%" stopColor="#FFF7F0" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#FAFAFA" stopOpacity="0" />
          </radialGradient>

          {/* Distant soft blue-gray mountain gradient */}
          <linearGradient id="distantMountain" x1="300" y1="100" x2="300" y2="370" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#E4ECF6" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#EDF3F9" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#FAFAFA" stopOpacity="0.95" />
          </linearGradient>

          {/* Mid-ground mountain gradient */}
          <linearGradient id="midMountain" x1="300" y1="150" x2="300" y2="370" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#CFDFEF" stopOpacity="0.85" />
            <stop offset="45%" stopColor="#DCE7F3" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#FAFAFA" stopOpacity="0.95" />
          </linearGradient>

          {/* Foreground ridge gradient */}
          <linearGradient id="foregroundRidge" x1="300" y1="210" x2="300" y2="370" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#BAD0E6" stopOpacity="0.8" />
            <stop offset="40%" stopColor="#D1E0EE" stopOpacity="0.75" />
            <stop offset="100%" stopColor="#FAFAFA" stopOpacity="0.9" />
          </linearGradient>

          {/* Road gradient */}
          <linearGradient id="roadFill" x1="20" y1="370" x2="620" y2="150" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.98" />
            <stop offset="50%" stopColor="#F8FAFC" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#EEF4F9" stopOpacity="0.9" />
          </linearGradient>
        </defs>

        {/* 1. Subtle warm sun */}
        <circle cx="500" cy="105" r="76" fill="url(#sunGradient)" />

        {/* 2. Distant mountain ridge */}
        <path
          d="M 0 240 C 90 180 180 145 280 160 C 370 175 440 105 520 115 C 575 122 610 102 640 110 L 640 370 L 0 370 Z"
          fill="url(#distantMountain)"
        />

        {/* 3. Mid-ground mountain ridge */}
        <path
          d="M 0 280 C 110 210 200 190 300 205 C 400 220 460 160 540 175 C 585 185 615 168 640 175 L 640 370 L 0 370 Z"
          fill="url(#midMountain)"
        />

        {/* 4. Foreground ridge / slope */}
        <path
          d="M 0 330 C 120 270 230 250 330 260 C 430 270 510 230 580 245 C 605 250 625 244 640 248 L 640 370 L 0 370 Z"
          fill="url(#foregroundRidge)"
        />

        {/* 5. Serene Winding Career Path */}
        <path
          d="M 20 370 C 65 332 115 296 175 276 C 235 256 295 249 365 227 C 425 207 485 187 545 167 C 585 154 615 147 640 143 L 640 149 C 615 153 585 160 545 173 C 485 193 425 213 365 233 C 295 255 235 262 175 282 C 115 302 65 338 20 370 Z"
          fill="url(#roadFill)"
          stroke="#CAD7E5"
          strokeWidth="0.8"
        />

        {/* Subtle Path Guide Line */}
        <path
          d="M 20 370 C 65 335 115 299 175 279 C 235 259 295 252 365 230 C 425 210 485 190 545 170 C 585 157 615 150 640 146"
          stroke="#B8CBDE"
          strokeWidth="0.75"
          strokeDasharray="3 3"
          fill="none"
          opacity="0.6"
        />

        {/* 6. Stylized Pine Trees on the right slope */}
        <g fill="#5F7696" opacity="0.85">
          <polygon points="535,270 530,284 540,284" />
          <polygon points="535,264 531,274 539,274" />
          <polygon points="535,259 532,267 538,267" />
          <rect x="534.5" y="284" width="1" height="3" fill="#4B607D" />

          <polygon points="548,262 542,277 554,277" />
          <polygon points="548,255 543,266 553,266" />
          <polygon points="548,249 544,258 552,258" />
          <rect x="547.5" y="277" width="1" height="3" fill="#4B607D" />

          <polygon points="560,256 555,269 565,269" />
          <polygon points="560,250 556,259 564,259" />
          <polygon points="560,245 557,253 563,253" />
          <rect x="559.5" y="269" width="1" height="3" fill="#4B607D" />

          <polygon points="572,250 566,265 578,265" />
          <polygon points="572,243 567,253 577,253" />
          <polygon points="572,237 568,246 576,246" />
          <rect x="571.5" y="265" width="1" height="3" fill="#4B607D" />

          <polygon points="584,242 579,255 589,255" />
          <polygon points="584,236 580,245 588,245" />
          <polygon points="584,231 581,239 587,239" />
          <rect x="583.5" y="255" width="1" height="3" fill="#4B607D" />

          <polygon points="596,236 591,248 601,248" />
          <polygon points="596,230 592,239 600,239" />
          <polygon points="596,225 593,233 599,233" />
          <rect x="595.5" y="248" width="1" height="3" fill="#4B607D" />
        </g>

        {/* 7. Journey Marker 1: Plan */}
        <g className="journey-marker-1">
          {/* Dot on road */}
          <circle cx="150" cy="286" r="3.5" fill="#1B2A4A" />
          {/* Hairline extending up */}
          <line x1="150" y1="286" x2="150" y2="202" stroke="#1B2A4A" strokeWidth="0.85" opacity="0.45" />
          {/* Marker label */}
          <text x="158" y="209" className="font-serif text-[16px] font-medium fill-[#1B2A4A]">
            Plan
          </text>
          <text x="158" y="224" className="font-sans text-[11px] fill-[#6B6B6B]">
            Know your direction
          </text>
        </g>

        {/* 8. Journey Marker 2: Apply */}
        <g className="journey-marker-2">
          {/* Dot on road */}
          <circle cx="325" cy="239" r="3.5" fill="#1B2A4A" />
          {/* Hairline extending up */}
          <line x1="325" y1="239" x2="325" y2="154" stroke="#1B2A4A" strokeWidth="0.85" opacity="0.45" />
          {/* Marker label */}
          <text x="333" y="161" className="font-serif text-[16px] font-medium fill-[#1B2A4A]">
            Apply
          </text>
          <text x="333" y="176" className="font-sans text-[11px] fill-[#6B6B6B]">
            Take action with clarity
          </text>
        </g>

        {/* 9. Journey Marker 3: Grow */}
        <g className="journey-marker-3">
          {/* Dot on road */}
          <circle cx="485" cy="186" r="3.5" fill="#1B2A4A" />
          {/* Hairline extending up */}
          <line x1="485" y1="186" x2="485" y2="102" stroke="#1B2A4A" strokeWidth="0.85" opacity="0.45" />
          {/* Marker label */}
          <text x="493" y="109" className="font-serif text-[16px] font-medium fill-[#1B2A4A]">
            Grow
          </text>
          <text x="493" y="124" className="font-sans text-[11px] fill-[#6B6B6B]">
            Turn effort into progress
          </text>
        </g>
      </svg>
    </div>
  );
};
