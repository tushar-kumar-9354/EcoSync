import { clsx } from 'clsx';
import { cva, type VariantProps } from 'class-variance-authority';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: any[]) {
  return twMerge(clsx(inputs));
}

export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-bg-primary disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-bg-primary hover:bg-primary-light',
        secondary: 'bg-bg-elevated text-white hover:bg-bg-tertiary',
        ghost: 'hover:bg-bg-elevated text-gray-300',
        danger: 'bg-severity-critical text-white hover:opacity-90',
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-4 text-sm',
        lg: 'h-12 px-6 text-base',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: { variant: 'default', size: 'md' },
  }
);

export function Button({ className, variant, size, ...props }: any) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

export function Card({ className, ...props }: any) {
  return (
    <div
      className={cn('rounded-xl bg-bg-secondary border border-bg-tertiary p-4', className)}
      {...props}
    />
  );
}

export function Badge({ className, variant = 'default', ...props }: any) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        {
          'bg-primary/20 text-primary': variant === 'default',
          'bg-severity-critical/20 text-severity-critical': variant === 'critical',
          'bg-severity-high/20 text-severity-high': variant === 'high',
          'bg-severity-medium/20 text-severity-medium': variant === 'medium',
          'bg-severity-low/20 text-severity-low': variant === 'low',
        },
        className
      )}
      {...props}
    />
  );
}

export function Spinner({ className }: any) {
  return (
    <svg className={cn('animate-spin h-5 w-5', className)} viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

export function Progress({ value, max = 100, className, color }: any) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className={cn('h-2 rounded-full bg-bg-tertiary overflow-hidden', className)}>
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${pct}%`, backgroundColor: color || 'var(--color-primary)' }}
      />
    </div>
  );
}

export function Sparkline({ data, width = 80, height = 30, color = '#00C853' }: {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" />
    </svg>
  );
}
