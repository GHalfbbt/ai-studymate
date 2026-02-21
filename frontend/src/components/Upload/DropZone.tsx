/**
 * Drag-and-drop file upload component.
 *
 * Uses react-dropzone for file selection with visual feedback.
 * Shows upload progress and file validation errors.
 */

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadDocument } from '../../api/documents';
import { formatFileSize } from '../../utils/formatters';
import Spinner from '../common/Spinner';

interface DropZoneProps {
    /** Subject ID to upload documents to */
    subjectId: string;
    /** Callback when upload completes successfully */
    onUploadComplete?: () => void;
}

// Accepted file types and their MIME types
const ACCEPTED_TYPES = {
    'application/pdf': ['.pdf'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/vnd.oasis.opendocument.text': ['.odt'],
    'text/plain': ['.txt'],
    'image/png': ['.png'],
    'image/jpeg': ['.jpg', '.jpeg'],
};

// Maximum file size: 50MB (must match backend MAX_UPLOAD_SIZE)
const MAX_SIZE = 50 * 1024 * 1024;

export default function DropZone({ subjectId, onUploadComplete }: DropZoneProps) {
    const [isUploading, setIsUploading] = useState(false);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

    const onDrop = useCallback(
        async (acceptedFiles: File[]) => {
            if (acceptedFiles.length === 0) return;

            setIsUploading(true);
            setUploadError(null);
            setUploadSuccess(null);

            try {
                // Upload files sequentially
                for (const file of acceptedFiles) {
                    await uploadDocument(file, { subject_id: subjectId });
                }

                const fileNames = acceptedFiles.map((f) => f.name).join(', ');
                setUploadSuccess(
                    `Successfully uploaded: ${fileNames}. Processing will begin shortly.`
                );

                // Notify parent to refresh document list
                onUploadComplete?.();
            } catch (error: unknown) {
                const message =
                    error instanceof Error ? error.message : 'Upload failed. Please try again.';
                setUploadError(message);
            } finally {
                setIsUploading(false);
            }
        },
        [subjectId, onUploadComplete]
    );

    const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
        onDrop,
        accept: ACCEPTED_TYPES,
        maxSize: MAX_SIZE,
        disabled: isUploading,
        multiple: true,
    });

    return (
        <div className="space-y-3">
            {/* Drop zone area */}
            <div
                {...getRootProps()}
                className={`dropzone ${isDragActive ? 'dropzone-active' : ''} ${isUploading ? 'opacity-50 cursor-wait' : ''
                    }`}
            >
                <input {...getInputProps()} />

                {isUploading ? (
                    <div className="flex flex-col items-center gap-3">
                        <Spinner size="lg" label="Uploading..." />
                    </div>
                ) : isDragActive ? (
                    <div className="flex flex-col items-center gap-3 animate-pulse-soft">
                        <span className="text-5xl">📥</span>
                        <p className="text-primary-300 font-semibold text-lg">
                            Drop files here
                        </p>
                    </div>
                ) : (
                    <div className="flex flex-col items-center gap-3">
                        <span className="text-5xl opacity-60">📂</span>
                        <div>
                            <p className="text-surface-100 font-semibold text-lg">
                                Drag & drop your study materials
                            </p>
                            <p className="text-surface-200/40 text-sm mt-1">
                                or <span className="text-primary-400 underline">browse files</span>
                            </p>
                        </div>
                        <div className="flex items-center gap-4 mt-2 text-xs text-surface-200/30">
                            <span>📄 PDF</span>
                            <span>📝 DOCX</span>
                            <span>📋 ODT</span>
                            <span>📃 TXT</span>
                            <span>🖼️ Images</span>
                            <span>• Max {formatFileSize(MAX_SIZE)}</span>
                        </div>
                    </div>
                )}
            </div>

            {/* File rejection errors */}
            {fileRejections.length > 0 && (
                <div className="p-3 rounded-xl bg-danger-500/10 border border-danger-500/20 text-danger-400 text-sm animate-slide-up">
                    {fileRejections.map(({ file, errors }) => (
                        <div key={file.name}>
                            <strong>{file.name}</strong>:{' '}
                            {errors.map((e) => e.message).join(', ')}
                        </div>
                    ))}
                </div>
            )}

            {/* Upload error */}
            {uploadError && (
                <div className="p-3 rounded-xl bg-danger-500/10 border border-danger-500/20 text-danger-400 text-sm animate-slide-up">
                    ❌ {uploadError}
                </div>
            )}

            {/* Upload success */}
            {uploadSuccess && (
                <div className="p-3 rounded-xl bg-success-500/10 border border-success-500/20 text-success-400 text-sm animate-slide-up">
                    ✅ {uploadSuccess}
                </div>
            )}
        </div>
    );
}
