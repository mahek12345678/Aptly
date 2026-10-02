import React from 'react';

interface MatchMapProps {
  matchedSkills: string[];
  missingSkills?: string[];
  roleSkills?: string[];
}

export const MatchMapVisual: React.FC<MatchMapProps> = ({
  matchedSkills = [],
  missingSkills = [],
  roleSkills = [],
}) => {
  // Determine top pairs to visualize (max 5 rows to keep it compact and memorable)
  const rows: Array<{
    resumeSkill: string;
    roleSkill: string;
    type: 'matched' | 'related' | 'missing';
  }> = [];

  // 1. Direct and related matches
  matchedSkills.slice(0, 4).forEach((skill, idx) => {
    const roleEquivalent = roleSkills[idx] || skill;
    rows.push({
      resumeSkill: skill,
      roleSkill: roleEquivalent,
      type: idx === 1 ? 'related' : 'matched',
    });
  });

  // 2. Missing gap (if any)
  if (missingSkills.length > 0 && rows.length < 5) {
    rows.push({
      resumeSkill: '—',
      roleSkill: missingSkills[0],
      type: 'missing',
    });
  }

  // Fallback defaults if list is brief
  if (rows.length === 0) {
    rows.push(
      { resumeSkill: 'Core Tech Stack', roleSkill: 'Requirements', type: 'matched' },
      { resumeSkill: 'Problem Solving', roleSkill: 'System Design', type: 'related' }
    );
  }

  return (
    <div className="p-4 rounded-xl border border-[#E2E2E2] bg-[#FAFAFA] space-y-3">
      <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-[#6B6B6B] border-b border-[#E2E2E2] pb-2">
        <span>YOUR RESUME</span>
        <span className="text-[#9CA3AF]">RESUME ↔ ROLE MATCH MAP</span>
        <span>ROLE NEEDS</span>
      </div>

      <div className="space-y-2.5">
        {rows.map((row, i) => (
          <div key={i} className="flex items-center justify-between text-[12.5px] font-medium">
            {/* Left: Resume Skill */}
            <span
              className={`w-28 text-left truncate ${
                row.type === 'missing' ? 'text-[#9CA3AF] italic' : 'text-[#1A1A1A]'
              }`}
            >
              {row.resumeSkill}
            </span>

            {/* Middle: Connector Line */}
            <div className="flex-1 mx-3 flex items-center justify-center relative">
              {row.type === 'matched' ? (
                <div className="w-full flex items-center">
                  <span className="w-2 h-2 rounded-full bg-[#1B2A4A] shrink-0" />
                  <div className="flex-1 h-[1.5px] bg-[#1B2A4A]" />
                  <span className="w-2 h-2 rounded-full bg-[#1B2A4A] shrink-0" />
                </div>
              ) : row.type === 'related' ? (
                <div className="w-full flex items-center">
                  <span className="w-2 h-2 rounded-full bg-[#3D5580] shrink-0" />
                  <div className="flex-1 h-[1.5px] bg-[#3D5580]" />
                  <span className="w-2 h-2 rounded-full bg-[#3D5580] shrink-0" />
                </div>
              ) : (
                <div className="w-full flex items-center">
                  <span className="w-2 h-2 rounded-full border border-[#9CA3AF] bg-white shrink-0" />
                  <div className="flex-1 border-t border-dashed border-[#CBD5E1]" />
                  <span className="w-2 h-2 rounded-full bg-[#9CA3AF] shrink-0" />
                </div>
              )}
            </div>

            {/* Right: Role Skill */}
            <span
              className={`w-28 text-right truncate ${
                row.type === 'missing' ? 'text-[#1B2A4A] font-semibold' : 'text-[#1A1A1A]'
              }`}
            >
              {row.roleSkill}
            </span>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 pt-1 text-[10.5px] text-[#6B6B6B]">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#1B2A4A]" />
          <span>Direct Match</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#3D5580]" />
          <span>Semantic Match</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full border border-[#9CA3AF] bg-white" />
          <span>Gap / Target</span>
        </div>
      </div>
    </div>
  );
};
