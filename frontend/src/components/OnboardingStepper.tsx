import { Check } from 'lucide-react';

interface StepItem {
  id: number;
  label: string;
}

const STEPS: StepItem[] = [
  { id: 1, label: 'About You' },
  { id: 2, label: 'Resume' },
  { id: 3, label: 'Personalize' },
  { id: 4, label: 'All Set' },
];

interface OnboardingStepperProps {
  currentStep: number;
}

export default function OnboardingStepper({ currentStep = 1 }: OnboardingStepperProps) {
  return (
    <div className="w-full max-w-xl sm:max-w-2xl mx-auto py-2">
      <div className="flex items-center justify-between relative">
        {STEPS.map((step, idx) => {
          const isActive = step.id === currentStep;
          const isCompleted = step.id < currentStep;
          const isLast = idx === STEPS.length - 1;

          return (
            <div key={step.id} className="flex items-center flex-1 last:flex-initial">
              {/* Step indicator circle and label */}
              <div className="flex flex-col items-center relative z-10">
                <div
                  className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-all duration-300 ${
                    isActive
                      ? 'bg-[#1E4280] text-white shadow-sm ring-4 ring-[#1E4280]/10'
                      : isCompleted
                      ? 'bg-[#1E4280] text-white'
                      : 'bg-[#EEF2F6] text-[#64748B]'
                  }`}
                >
                  {isCompleted ? (
                    <Check size={14} strokeWidth={2.8} />
                  ) : (
                    <span>{step.id}</span>
                  )}
                </div>
                <span
                  className={`text-[11.5px] sm:text-[12px] tracking-tight mt-1.5 whitespace-nowrap transition-colors duration-200 ${
                    isActive
                      ? 'font-semibold text-[#111827]'
                      : isCompleted
                      ? 'font-medium text-[#111827]'
                      : 'font-normal text-[#64748B]'
                  }`}
                >
                  {step.label}
                </span>
              </div>

              {/* Connecting line to next step */}
              {!isLast && (
                <div className="flex-1 mx-2 sm:mx-3 h-[2px] bg-[#E2E8F0] relative -top-3 overflow-hidden rounded-full">
                  <div
                    className="h-full bg-[#1E4280] transition-all duration-500 ease-out"
                    style={{
                      width: isCompleted ? '100%' : '0%',
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
