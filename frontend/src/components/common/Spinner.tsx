/**
 * Common reusable Spinner component.
 *
 * Displays a loading spinner with optional label text.
 */

interface SpinnerProps {
    /** Optional size variant */
    size?: 'sm' | 'md' | 'lg';
    /** Optional label text below the spinner */
    label?: string;
}

export default function Spinner({ size = 'md', label }: SpinnerProps) {
    const sizeClasses = {
        sm: 'w-4 h-4 border-2',
        md: 'w-8 h-8 border-3',
        lg: 'w-12 h-12 border-4',
    };

    return (
        <div className="flex flex-col items-center gap-3">
            <div
                className={`${sizeClasses[size]} rounded-full border-primary-200/20 border-t-primary-500 animate-spin`}
            />
            {label && (
                <p className="text-sm text-surface-200/60 animate-pulse-soft">{label}</p>
            )}
        </div>
    );
}
