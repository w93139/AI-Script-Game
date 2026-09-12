import { useId } from 'react';
import * as Select from '@radix-ui/react-select';

const valuePrefix = 'play-option:';
export default function PlaySelect({ label, value, options, placeholder = '请选择', disabled, onChange, presentation = 'dropdown' }: {
  label: string; value: string; options: { value: string; label: string }[];
  presentation?: 'dropdown' | 'choices';
  placeholder?: string; disabled?: boolean; onChange: (value: string) => void;
}) {
  const groupId = useId();
  if (presentation === 'choices') return <span role="radiogroup" aria-label={label} className="mt-2 flex flex-wrap gap-2">
    {options.map(option => <label key={option.value} className="relative min-w-24 cursor-pointer">
      <input type="radio" name={groupId} value={option.value} checked={value === option.value} disabled={disabled}
        onChange={() => { if (!disabled) onChange(option.value); }} className="peer sr-only" />
      <span className="flex min-h-11 items-center justify-center gap-2 rounded-md border border-line bg-ink px-4 py-3 text-sm text-paper transition-colors hover:border-faint peer-checked:border-mist peer-checked:bg-white/15 peer-checked:text-mist peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-mist peer-disabled:cursor-not-allowed peer-disabled:opacity-40">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/10 text-mist" aria-hidden="true">{option.label.slice(0, 1)}</span>
        {option.label}<span aria-hidden="true" className={value === option.value ? 'visible' : 'invisible'}>✓</span>
      </span>
    </label>)}
    {!options.length && <span className="text-sm text-mist">暂无可选择的角色。</span>}
  </span>;
  return <Select.Root value={valuePrefix + value} disabled={disabled} onValueChange={v => onChange(v.slice(valuePrefix.length))}>
    <Select.Trigger aria-label={label} className="mt-2 flex w-full min-w-0 items-center justify-between gap-3 rounded-md border border-line bg-ink px-4 py-3 text-left text-sm text-paper outline-none transition focus:border-mist focus:ring-2 focus:ring-mist/20 disabled:cursor-not-allowed disabled:opacity-50">
      <span className="min-w-0 truncate"><Select.Value>{options.find(o => o.value === value)?.label || placeholder}</Select.Value></span><Select.Icon className="text-mist">⌄</Select.Icon>
    </Select.Trigger>
    <Select.Portal><Select.Content position="popper" sideOffset={6} className="z-[100] max-h-[min(18rem,var(--radix-select-content-available-height))] w-[var(--radix-select-trigger-width)] overflow-hidden rounded-xl border border-line bg-panel p-1.5 text-paper shadow-sm">
      <Select.ScrollUpButton className="text-center text-mist">⌃</Select.ScrollUpButton>
      <Select.Viewport>{(!options.some(o => o.value === '') ? [{ value: '', label: placeholder }, ...options] : options).map(option => <Select.Item key={option.value} value={valuePrefix + option.value} className="relative flex min-h-11 cursor-pointer select-none items-center rounded-md py-2 pl-9 pr-3 text-sm outline-none data-[highlighted]:bg-white/15 data-[highlighted]:text-mist data-[state=checked]:bg-white/10">
        <Select.ItemIndicator className="absolute left-3 text-mist">✓</Select.ItemIndicator><Select.ItemText>{option.label}</Select.ItemText>
      </Select.Item>)}</Select.Viewport>
      <Select.ScrollDownButton className="text-center text-mist">⌄</Select.ScrollDownButton>
    </Select.Content></Select.Portal>
  </Select.Root>;
}
