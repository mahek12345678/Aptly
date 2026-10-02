import { useState, type KeyboardEvent, type ClipboardEvent } from 'react';
import { X } from 'lucide-react';

interface TagInputProps {
  id?: string;
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  helperText?: string;
  suggestions?: string[];
}

export default function TagInput({
  id,
  tags,
  onChange,
  placeholder = 'Type and press comma or enter...',
  helperText,
  suggestions = [],
}: TagInputProps) {
  const [inputValue, setInputValue] = useState('');

  const addTag = (value: string) => {
    const trimmed = value.trim().replace(/^,+|,+$/g, '');
    if (!trimmed) return;

    // Check if multiple comma-separated values exist
    const items = trimmed
      .split(',')
      .map((item) => item.trim())
      .filter((item) => item.length > 0 && !tags.includes(item));

    if (items.length > 0) {
      onChange([...tags, ...items]);
    }
    setInputValue('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addTag(inputValue);
    } else if (e.key === 'Backspace' && !inputValue && tags.length > 0) {
      // Remove last tag if input is empty
      e.preventDefault();
      removeTag(tags.length - 1);
    }
  };

  const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasteData = e.clipboardData.getData('text');
    addTag(pasteData);
  };

  const handleBlur = () => {
    if (inputValue.trim()) {
      addTag(inputValue);
    }
  };

  const removeTag = (indexToRemove: number) => {
    onChange(tags.filter((_, i) => i !== indexToRemove));
  };

  return (
    <div className="w-full">
      <div className="min-h-[46px] w-full px-3 py-1.5 bg-white border border-[#D1D5DB] rounded-lg shadow-sm focus-within:border-[#1B2A4A] focus-within:ring-1 focus-within:ring-[#1B2A4A] transition-subtle flex flex-wrap items-center gap-1.5">
        {tags.map((tag, idx) => (
          <span
            key={`${tag}-${idx}`}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-[#EAEFF8] text-[#1B2A4A] border border-[#CBD9EE] animate-fade-in"
          >
            <span>{tag}</span>
            <button
              type="button"
              onClick={() => removeTag(idx)}
              className="text-[#4B5E80] hover:text-[#1B2A4A] focus:outline-none ml-0.5"
              aria-label={`Remove tag ${tag}`}
            >
              <X size={12} strokeWidth={2.5} />
            </button>
          </span>
        ))}

        <input
          id={id}
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          onBlur={handleBlur}
          placeholder={tags.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[140px] text-sm text-text placeholder:text-[#9CA3AF] bg-transparent border-none outline-none py-1 px-1 focus:ring-0"
        />
      </div>

      {/* Helper text or suggestions */}
      <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2">
        {helperText && (
          <p className="text-xs text-muted">{helperText}</p>
        )}

        {suggestions.length > 0 && tags.length < suggestions.length && (
          <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted">
            <span className="text-[11px] text-muted">Suggestions:</span>
            {suggestions
              .filter((s) => !tags.includes(s))
              .slice(0, 3)
              .map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => onChange([...tags, suggestion])}
                  className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-[#334155] rounded-full text-[11px] font-medium transition-subtle"
                >
                  + {suggestion}
                </button>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}
