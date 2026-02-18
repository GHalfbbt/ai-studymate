/**
 * Formatting utility functions.
 */

/**
 * Format file size in bytes to a human-readable string.
 *
 * @param bytes - File size in bytes
 * @returns Formatted string (e.g., "1.5 MB")
 */
export function formatFileSize(bytes: number | null): string {
    if (bytes === null || bytes === 0) return '0 B';

    const units = ['B', 'KB', 'MB', 'GB'];
    const k = 1024;
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    const size = bytes / Math.pow(k, i);

    return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

/**
 * Format a date string to a localized display format.
 *
 * @param dateString - ISO date string
 * @returns Formatted date (e.g., "Feb 18, 2025")
 */
export function formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
}

/**
 * Format a date string to include time.
 *
 * @param dateString - ISO date string
 * @returns Formatted date and time (e.g., "Feb 18, 2025 3:30 PM")
 */
export function formatDateTime(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
    });
}

/**
 * Truncate text to a maximum length with ellipsis.
 *
 * @param text - Text to truncate
 * @param maxLength - Maximum character length
 * @returns Truncated text
 */
export function truncateText(text: string, maxLength: number = 100): string {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength).trim() + '...';
}

/**
 * Get file type icon name based on file extension.
 *
 * @param fileType - File type (pdf, docx, txt, image)
 * @returns Emoji icon for the file type
 */
export function getFileTypeIcon(fileType: string): string {
    const icons: Record<string, string> = {
        pdf: '📄',
        docx: '📝',
        txt: '📃',
        image: '🖼️',
    };
    return icons[fileType] || '📁';
}

/**
 * Get processing status badge variant.
 *
 * @param status - Document processing status
 * @returns CSS class for the status badge
 */
export function getStatusBadgeClass(status: string): string {
    const classes: Record<string, string> = {
        pending: 'badge-warning',
        processing: 'badge-info',
        completed: 'badge-success',
        failed: 'badge-danger',
    };
    return classes[status] || 'badge-info';
}
