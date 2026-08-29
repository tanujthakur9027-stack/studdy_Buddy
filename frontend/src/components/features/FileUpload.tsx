"use client";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, FileText, X, CheckCircle2, AlertCircle } from "lucide-react";
import { uploadDocument } from "@/lib/api";
import { Spinner } from "@/components/ui";
import type { UploadedDocument } from "@/types";
import toast from "react-hot-toast";
import { clsx } from "clsx";

interface Props {
  onUploaded: (_doc: UploadedDocument) => void;
  documents: UploadedDocument[];
  onRemove: (_docId: string) => void;
}

export function FileUpload({ onUploaded, documents, onRemove }: Props) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    async (accepted: File[]) => {
      if (!accepted.length) return;
      setError(null);
      setUploading(true);
      for (const file of accepted) {
        try {
          const result = await uploadDocument(file);
          onUploaded({ ...result, uploadedAt: new Date() });
          toast.success(`"${file.name}" uploaded — ${result.chunks} chunks indexed`);
        } catch (e: unknown) {
          const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Upload failed";
          setError(msg);
          toast.error(msg);
        }
      }
      setUploading(false);
    },
    [onUploaded]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf":   [".pdf"],
      "text/plain":        [".txt", ".bin"],
      "text/markdown":     [".md"],
      "application/msword": [".doc"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/octet-stream": [".bin"],
    },
    maxSize: 20 * 1024 * 1024,
    disabled: uploading,
    onDropRejected: (files) => {
      const reason = files[0]?.errors?.[0]?.message || "File rejected";
      setError(reason);
      toast.error(reason);
    },
  });

  return (
    <div className="space-y-5">
      <div
        {...getRootProps()}
        className={clsx(
          "relative flex flex-col items-center justify-center gap-4 p-10 rounded-2xl border-2 border-dashed cursor-pointer transition-all duration-300",
          isDragActive
            ? "border-brand-500 bg-brand-500/10"
            : "border-gray-700 hover:border-brand-600 hover:bg-gray-900/40",
          uploading && "pointer-events-none opacity-60"
        )}
      >
        <input {...getInputProps()} />
        <motion.div
          animate={isDragActive ? { scale: 1.15 } : { scale: 1 }}
          className="p-4 rounded-2xl bg-brand-500/10 text-brand-400"
        >
          {uploading ? <Spinner size="lg" /> : <UploadCloud className="h-10 w-10" />}
        </motion.div>
        <div className="text-center">
          <p className="text-base font-semibold text-gray-200">
            {isDragActive ? "Drop files here" : "Drag & drop your notes or syllabus"}
          </p>
          <p className="text-sm text-gray-500 mt-1">PDF, TXT, MD, DOC, DOCX, BIN — up to 20 MB each</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          className="btn-primary"
          type="button"
        >
          Browse Files
        </motion.button>
      </div>

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/25 text-red-400 text-sm"
          >
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {documents.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
            Indexed Documents ({documents.length})
          </p>
          <div className="space-y-2">
            {documents.map((doc) => (
              <motion.div
                key={doc.doc_id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                className="flex items-center gap-3 p-3 rounded-xl bg-gray-900 border border-gray-800"
              >
                <CheckCircle2 className="h-4 w-4 text-green-400 shrink-0" />
                <FileText className="h-4 w-4 text-brand-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-200 truncate">{doc.filename}</p>
                  <p className="text-xs text-gray-500">{doc.chunks} chunks · {doc.uploadedAt.toLocaleTimeString()}</p>
                </div>
                <button
                  onClick={() => onRemove(doc.doc_id)}
                  className="p-1 rounded-lg hover:bg-gray-700 text-gray-500 hover:text-gray-300 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
