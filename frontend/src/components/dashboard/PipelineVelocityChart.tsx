import React, { useState, useMemo } from 'react';
import { BarChart3 } from 'lucide-react';
import { JobApplication } from '@/types/application';

interface PipelineVelocityChartProps {
  applications: JobApplication[];
}

type Timeframe = '30d' | '90d' | 'all';

interface WeeklyBucket {
  label: string;
  appsCount: number;
  interviewsCount: number;
  yieldPct: number;
}

export const PipelineVelocityChart: React.FC<PipelineVelocityChartProps> = ({
  applications,
}) => {
  const [timeframe, setTimeframe] = useState<Timeframe>('30d');

  // Compute weekly buckets dynamically from real application data
  const { buckets, avgYield, hasData } = useMemo(() => {
    const now = new Date();

    // Determine number of weeks and start point
    const numWeeks = timeframe === '30d' ? 4 : timeframe === '90d' ? 8 : 6;
    const bucketDays = timeframe === '90d' ? 11 : 7;
    const result: WeeklyBucket[] = [];

    // Helper to format short date label, e.g. "Oct 2"
    const formatShortDate = (date: Date) => {
      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
      }).format(date);
    };

    let totalAppsInWindow = 0;
    let totalInterviewsInWindow = 0;

    for (let i = numWeeks - 1; i >= 0; i--) {
      const bucketEnd = new Date(now.getTime() - i * bucketDays * 24 * 60 * 60 * 1000);
      const bucketStart = new Date(
        bucketEnd.getTime() - bucketDays * 24 * 60 * 60 * 1000
      );

      // Filter applications created or applied within this time bucket
      const matchingApps = applications.filter((app) => {
        const rawDate = app.applied_at || app.created_at;
        if (!rawDate) return false;
        const appDate = new Date(rawDate);
        return appDate >= bucketStart && appDate < bucketEnd;
      });

      const appsCount = matchingApps.length;
      // Applications that progressed to interview or offer
      const interviewsCount = matchingApps.filter((a) =>
        ['interview', 'offer'].includes(a.status?.toLowerCase())
      ).length;

      totalAppsInWindow += appsCount;
      totalInterviewsInWindow += interviewsCount;

      const yieldPct =
        appsCount > 0 ? Number(((interviewsCount / appsCount) * 100).toFixed(1)) : 0;

      const weekNumber = numWeeks - i;
      const label =
        timeframe === '30d'
          ? `Week ${weekNumber} (${formatShortDate(bucketStart)})`
          : `${formatShortDate(bucketStart)} - ${formatShortDate(bucketEnd)}`;

      result.push({
        label,
        appsCount,
        interviewsCount,
        yieldPct,
      });
    }

    const calculatedAvgYield =
      totalAppsInWindow > 0
        ? ((totalInterviewsInWindow / totalAppsInWindow) * 100).toFixed(1)
        : '0.0';

    return {
      buckets: result,
      avgYield: calculatedAvgYield,
      hasData: totalAppsInWindow > 0,
    };
  }, [applications, timeframe]);

  // Chart layout dimensions for crisp SVG rendering
  const svgWidth = 560;
  const svgHeight = 150;
  const chartPaddingTop = 20;
  const chartPaddingBottom = 30;
  const chartPaddingLeft = 30;
  const chartPaddingRight = 20;

  const innerWidth = svgWidth - chartPaddingLeft - chartPaddingRight;
  const innerHeight = svgHeight - chartPaddingTop - chartPaddingBottom;

  // Max value calculation for Y axis scale (at least 4 to have nice ticks)
  const maxVal = useMemo(() => {
    const highest = Math.max(...buckets.map((b) => Math.max(b.appsCount, b.interviewsCount)), 0);
    return Math.max(highest + 1, 4);
  }, [buckets]);

  // Coordinates for trend line connecting applications bars
  const trendLinePoints = useMemo(() => {
    if (buckets.length === 0) return '';
    return buckets
      .map((b, index) => {
        const x = chartPaddingLeft + (index + 0.5) * (innerWidth / buckets.length);
        const y =
          chartPaddingTop + innerHeight - (b.appsCount / maxVal) * innerHeight;
        return `${x},${y}`;
      })
      .join(' ');
  }, [buckets, innerWidth, innerHeight, maxVal]);

  return (
    <div className="rounded-lg border border-[#E2E2E2] bg-white p-5 sm:p-6 shadow-2xs flex flex-col justify-between">
      {/* Title & Timeframe Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3.5 pb-4 border-b border-[#F0F0F0]">
        <div>
          <h3 className="font-serif text-[18px] font-bold text-[#1A1A1A] tracking-tight flex items-center gap-2">
            <BarChart3 size={17} className="text-[#1B2A4A]" />
            <span>Pipeline Velocity & Yield</span>
          </h3>
          <p className="text-[12px] text-[#6B6B6B] mt-0.5">
            Weekly applications submitted vs interviews scheduled
          </p>
        </div>

        {/* Segmented Timeframe Controls */}
        <div className="inline-flex items-center rounded-md border border-[#E2E2E2] bg-[#F5F5F7] p-0.5 self-start sm:self-center">
          <button
            type="button"
            onClick={() => setTimeframe('30d')}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition-all cursor-pointer ${
              timeframe === '30d'
                ? 'bg-white text-[#1A1A1A] shadow-2xs font-semibold'
                : 'text-[#6B6B6B] hover:text-[#1A1A1A]'
            }`}
          >
            Last 30 Days
          </button>
          <button
            type="button"
            onClick={() => setTimeframe('90d')}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition-all cursor-pointer ${
              timeframe === '90d'
                ? 'bg-white text-[#1A1A1A] shadow-2xs font-semibold'
                : 'text-[#6B6B6B] hover:text-[#1A1A1A]'
            }`}
          >
            90 Days
          </button>
          <button
            type="button"
            onClick={() => setTimeframe('all')}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition-all cursor-pointer ${
              timeframe === 'all'
                ? 'bg-white text-[#1A1A1A] shadow-2xs font-semibold'
                : 'text-[#6B6B6B] hover:text-[#1A1A1A]'
            }`}
          >
            All-time
          </button>
        </div>
      </div>

      {/* Analytical Chart Visualizer */}
      <div className="py-4 relative w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-[180px] select-none"
        >
          {/* Subtle Horizontal Hairline Grid */}
          {[0, 0.33, 0.66, 1].map((ratio, i) => {
            const y = chartPaddingTop + innerHeight * (1 - ratio);
            return (
              <g key={i}>
                <line
                  x1={chartPaddingLeft}
                  y1={y}
                  x2={svgWidth - chartPaddingRight}
                  y2={y}
                  stroke="#F0F0F0"
                  strokeWidth="1"
                />
                <text
                  x={chartPaddingLeft - 6}
                  y={y + 3}
                  textAnchor="end"
                  fontSize="9"
                  fontFamily="monospace"
                  fill="#9CA3AF"
                >
                  {Math.round(maxVal * ratio)}
                </text>
              </g>
            );
          })}

          {/* Dual Bars for Each Week */}
          {buckets.map((b, index) => {
            const slotWidth = innerWidth / buckets.length;
            const centerX = chartPaddingLeft + (index + 0.5) * slotWidth;

            // Applications Bar (Dark navy)
            const appBarWidth = 14;
            const appBarHeight = (b.appsCount / maxVal) * innerHeight;
            const appBarY = chartPaddingTop + innerHeight - appBarHeight;
            const appBarX = centerX - appBarWidth - 2;

            // Interviews Yielded Bar (Narrow light blue)
            const intBarWidth = 9;
            const intBarHeight = (b.interviewsCount / maxVal) * innerHeight;
            const intBarY = chartPaddingTop + innerHeight - intBarHeight;
            const intBarX = centerX + 2;

            return (
              <g key={index} className="group cursor-default">
                {/* Apps Bar */}
                <rect
                  x={appBarX}
                  y={appBarY}
                  width={appBarWidth}
                  height={Math.max(appBarHeight, 2)}
                  rx="2"
                  fill="#1B2A4A"
                  className="transition-all duration-200 hover:opacity-85"
                >
                  <title>{`${b.appsCount} applications in ${b.label}`}</title>
                </rect>

                {/* Interviews Yielded Bar */}
                <rect
                  x={intBarX}
                  y={intBarY}
                  width={intBarWidth}
                  height={Math.max(intBarHeight, 2)}
                  rx="1.5"
                  fill="#8DA4C4"
                  className="transition-all duration-200 hover:opacity-85"
                >
                  <title>{`${b.interviewsCount} interviews yielded in ${b.label}`}</title>
                </rect>

                {/* X-axis Label */}
                <text
                  x={centerX}
                  y={svgHeight - 10}
                  textAnchor="middle"
                  fontSize="10"
                  fontFamily="Inter, sans-serif"
                  fill="#6B6B6B"
                >
                  {b.label}
                </text>
              </g>
            );
          })}

          {/* Restrained Trend Line across Applications */}
          {hasData && (
            <polyline
              fill="none"
              stroke="#1B2A4A"
              strokeWidth="1.25"
              strokeDasharray="3,3"
              opacity="0.6"
              points={trendLinePoints}
            />
          )}

          {/* Data Points on Trend Line */}
          {hasData &&
            buckets.map((b, index) => {
              const x =
                chartPaddingLeft + (index + 0.5) * (innerWidth / buckets.length);
              const y =
                chartPaddingTop + innerHeight - (b.appsCount / maxVal) * innerHeight;
              return (
                <circle
                  key={index}
                  cx={x}
                  cy={y}
                  r="2.5"
                  fill="#1B2A4A"
                  stroke="#FFFFFF"
                  strokeWidth="1"
                />
              );
            })}
        </svg>

        {/* Analytical Empty State Overlay if No Applications */}
        {!hasData && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/70 backdrop-blur-[1px] text-center p-4">
            <p className="text-[13px] font-medium text-[#1A1A1A]">
              No applications recorded in this window
            </p>
            <p className="text-[11.5px] text-[#6B6B6B] mt-0.5">
              Applications submitted and confirmed will appear in this velocity ledger
            </p>
          </div>
        )}
      </div>

      {/* Chart Footer: Legend and Avg Yield Metric */}
      <div className="pt-3 border-t border-[#F0F0F0] flex items-center justify-between text-[11.5px]">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-xs bg-[#1B2A4A]" />
            <span className="text-[#1A1A1A] font-medium">Applications</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-xs bg-[#8DA4C4]" />
            <span className="text-[#6B6B6B]">Interviews Yielded</span>
          </div>
        </div>

        <div className="text-[#1A1A1A] font-mono text-[11.5px]">
          <span className="text-[#6B6B6B]">Avg yield: </span>
          <span className="font-semibold text-[#1B2A4A]">{avgYield}%</span>
        </div>
      </div>
    </div>
  );
};
