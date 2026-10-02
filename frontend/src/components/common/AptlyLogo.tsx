import React from 'react';

/**
 * AptlyLogo — Canonical brand component.
 *
 * The geometric symbol acts as the "A":
 *   - Large dark navy triangle (forms the A peak & right side)
 *   - Small muted-blue triangle at bottom-left (the accent)
 * Followed immediately by the serif wordmark "ptly" in dark navy.
 *
 * Variants:
 *   "full"  — Symbol + "ptly" wordmark (default)
 *   "mark"  — Symbol only (icon/avatar/favicon use)
 */

interface AptlyLogoProps {
  /** "full" renders symbol + wordmark; "mark" renders the mark only */
  variant?: 'full' | 'mark';
  /** Logical height in px. Both mark and wordmark scale from this. */
  height?: number;
  className?: string;
}

/**
 * The "A" mark: viewBox 0 0 100 110
 *
 * The actual logo has:
 *   1. A dark-navy triangle that forms the top peak + right side
 *      (large A-shape without the left bottom leg)
 *   2. A muted-blue smaller triangle at bottom-left
 *
 * Vertices (derived from studying the logo):
 *   Dark navy: top-centre (50,0), top-right-outer (100,110), centre-bottom (50,70)
 *   Muted blue: centre-bottom (50,70), left-outer (0,110), centre-left (25,70)
 */
const MARK_SVG = (
  <React.Fragment>
    {/* Main dark navy "A" peak + right half */}
    <polygon points="50,0 100,110 50,68" fill="#1B2A4A" />
    {/* Left "leg" dark navy */}
    <polygon points="50,0 50,68 10,110" fill="#1B2A4A" />
    {/* Muted-blue accent triangle — bottom left */}
    <polygon points="10,110 50,68 0,110" fill="#7B9EC4" />
  </React.Fragment>
);

export const AptlyLogo: React.FC<AptlyLogoProps> = ({
  variant = 'full',
  height = 32,
  className = '',
}) => {
  // Mark aspect ratio from viewBox 100×110
  const markWidth = Math.round((height * 100) / 110);
  const markHeight = height;

  const MarkSvg = (
    <svg
      width={markWidth}
      height={markHeight}
      viewBox="0 0 100 110"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      style={{ display: 'block', flexShrink: 0 }}
    >
      {MARK_SVG}
    </svg>
  );

  if (variant === 'mark') {
    return (
      <span
        className={`inline-flex items-center ${className}`}
        aria-label="Aptly"
      >
        {MarkSvg}
      </span>
    );
  }

  // Wordmark "ptly" — rendered as HTML so real font rendering applies.
  // Gap between mark and text is ~6% of height to match tight logo spacing.
  const gap = Math.round(height * 0.1);
  const fontSize = Math.round(height * 1.18);

  return (
    <span
      className={`inline-flex items-center leading-none select-none ${className}`}
      aria-label="Aptly"
      style={{ gap: `${gap}px` }}
    >
      {MarkSvg}
      <span
        aria-hidden="true"
        style={{
          fontFamily: "Georgia, 'Times New Roman', serif",
          fontSize: `${fontSize}px`,
          fontWeight: 400,
          color: '#1B2A4A',
          lineHeight: 1,
          letterSpacing: '-0.01em',
          userSelect: 'none',
        }}
      >
        ptly
      </span>
    </span>
  );
};

export default AptlyLogo;
