"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import {
  UploadCloud, FileText, FileSpreadsheet, FileImage,
  Presentation, X, CheckCircle2, AlertCircle, Sparkles, Network,
  AlignLeft, Upload as UploadIcon,
} from "lucide-react";
import { uploadDocument } from "@/lib/api";
import { Spinner } from "@/components/ui";
import { CheatSheet } from "@/components/features/CheatSheet";
import { ConceptMapModal } from "@/components/features/ConceptMapModal";
import type { UploadedDocument } from "@/types";
import toast from "react-hot-toast";
import { clsx } from "clsx";

interface Props {
  onUploaded: (_doc: UploadedDocument) => void;
  documents: UploadedDocument[];
  onRemove: (_docId: string) => void;
  /** Called when the user pastes/types text instead of uploading a file */
  onTextInput?: (_text: string) => void;
  /** Currently active pasted text (controlled from parent, optional) */
  pastedText?: string;
}

type InputMode = "upload" | "text";

const IMAGE_EXTS = new Set(["png", "jpg", "jpeg", "webp", "jfif"]);

function isImageFile(filename: string) {
  return IMAGE_EXTS.has(filename.split(".").pop()?.toLowerCase() ?? "");
}

/** Returns the right icon component for a filename extension. */
function FileIcon({ filename, className }: { filename: string; className?: string }) {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  if (["xlsx", "xls"].includes(ext))
    return <FileSpreadsheet className={className} />;
  if (["png", "jpg", "jpeg", "webp", "jfif"].includes(ext))
    return <FileImage className={className} />;
  if (["ppt", "pptx"].includes(ext))
    return <Presentation className={className} />;
  return <FileText className={className} />;
}

export function FileUpload({ onUploaded, documents, onRemove, onTextInput, pastedText = "" }: Props) {
  const [inputMode,       setInputMode]       = useState<InputMode>("upload");
  const [uploading,       setUploading]       = useState(false);
  const [error,           setError]           = useState<string | null>(null);
  const [cheatSheetDoc,   setCheatSheetDoc]   = useState<UploadedDocument | null>(null);
  const [conceptMapDoc,   setConceptMapDoc]   = useState<UploadedDocument | null>(null);
  const [localText,       setLocalText]       = useState(pastedText);

  // Track preview URLs so we can revoke them when docs are removed (avoid memory leaks)
  const previewUrls = useRef<Map<string, string>>(new Map());

  // Revoke any object URLs for documents that have been removed
  useEffect(() => {
    const currentIds = new Set(documents.map((d) => d.doc_id));
    previewUrls.current.forEach((url, id) => {
      if (!currentIds.has(id)) {
        URL.revokeObjectURL(url);
        previewUrls.current.delete(id);
      }
    });
  }, [documents]);

  const onDrop = useCallback(
    async (accepted: File[]) => {
      if (!accepted.length) return;
      setError(null);
      setUploading(true);
      for (const file of accepted) {
        const previewUrl = isImageFile(file.name)
          ? URL.createObjectURL(file)
          : undefined;
        try {
          const result = await uploadDocument(file);
          if (previewUrl) previewUrls.current.set(result.doc_id, previewUrl);
          onUploaded({ ...result, uploadedAt: new Date(), previewUrl });
          toast.success(`"${file.name}" uploaded — ${result.chunks} chunks indexed`);
        } catch (e: unknown) {
          if (previewUrl) URL.revokeObjectURL(previewUrl);
          const msg =
            (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
            "Upload failed";
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
      // Documents
      "application/pdf":     [".pdf"],
      "text/plain":          [".txt", ".bin"],
      "text/markdown":       [".md"],
      "application/msword":  [".doc"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      // PowerPoint
      "application/vnd.ms-powerpoint": [".ppt"],
      "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
      // Excel
      "application/vnd.ms-excel": [".xls"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      // Images (OCR)
      "image/png":   [".png"],
      "image/jpeg":  [".jpg", ".jpeg", ".jfif"],
      "image/webp":  [".webp"],
      "image/jfif":  [".jfif"],
      "image/pjpeg": [".jpg", ".jpeg"],
      // Fallback for any mis-labelled file
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

  const handleTextChange = (val: string) => {
    setLocalText(val);
    onTextInput?.(val);
  };

  const MODES: { id: InputMode; label: string; icon: React.ElementType }[] = [
    { id: "upload", label: "Upload Document",  icon: UploadIcon },
    { id: "text",   label: "Paste / Type Text", icon: AlignLeft  },
  ];

  return (
    <>
    <div className="space-y-5">

      {/* ── Mode toggle tabs ── */}
      <div className="flex gap-1 p-1 bg-gray-800/60 rounded-xl border border-gray-700/50 w-fit">
        {MODES.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setInputMode(id)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
              inputMode === id
                ? "bg-blue-600 text-white shadow"
                : "text-gray-400 hover:text-white hover:bg-gray-700"
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {inputMode === "upload" ? (
          <motion.div
            key="upload"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
          >
            {/* ── Drop zone ── */}
            <div
              {...getRootProps()}
              className={clsx(
                "relative flex flex-col items-center justify-center gap-4 p-10 rounded-2xl border-2 border-dashed cursor-pointer transition-all duration-300",
                isDragActive
                  ? "border-blue-500 bg-blue-500/10"
                  : "border-gray-700 hover:border-blue-600 hover:bg-gray-900/40",
                uploading && "pointer-events-none opacity-60"
              )}
            >
              <input {...getInputProps()} />
              <motion.div
                animate={isDragActive ? { scale: 1.15 } : { scale: 1 }}
                className="p-4 rounded-2xl bg-blue-500/10 text-blue-400"
              >
                {uploading ? <Spinner size="lg" /> : <UploadCloud className="h-10 w-10" />}
              </motion.div>
              <div className="text-center">
                <p className="text-base font-semibold text-gray-200">
                  {isDragActive ? "Drop files here" : "Drag & drop your notes or syllabus"}
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  PDF · TXT · MD · DOC · DOCX · PPT · PPTX · XLSX · PNG · JPG · JPEG · WEBP · JFIF — up to 20 MB
                </p>
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
          </motion.div>
        ) : (
          <motion.div
            key="text"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
            className="space-y-3"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-gray-300">
                Paste or type your topic, notes, or any text to study
              </p>
              {localText.trim() && (
                <span className="text-xs text-blue-400 font-medium">
                  {localText.trim().split(/\s+/).length} words
                </span>
              )}
            </div>
            <textarea
              value={localText}
              onChange={(e) => handleTextChange(e.target.value)}
              placeholder="e.g. 'Explain Newton's laws of motion' or paste your lecture notes here…"
              rows={10}
              className="w-full bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition-all duration-200 resize-y leading-relaxed"
            />
            {localText.trim() && (
              <p className="text-xs text-gray-500 flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-green-400" />
                Text ready — switch to any AI tool tab above to generate study materials
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Error banner ── */}
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

      {/* ── Indexed documents list ── */}
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
                className="flex items-start gap-3 p-3 rounded-xl bg-gray-900 border border-gray-800"
              >
                <CheckCircle2 className="h-4 w-4 text-green-400 shrink-0 mt-0.5" />
                {doc.previewUrl ? (
                  <img
                    src={doc.previewUrl}
                    alt={doc.filename}
                    className="h-10 w-10 rounded-lg object-cover shrink-0 border border-gray-700"
                  />
                ) : (
                  <FileIcon filename={doc.filename} className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-200 truncate">{doc.filename}</p>
                  {doc.description && (
                    <p className="text-xs text-gray-400 mt-0.5 line-clamp-2 leading-relaxed">
                      {doc.description}
                    </p>
                  )}
                  <p className="text-xs text-gray-500 mt-1">
                    {doc.chunks} chunks · {doc.pages} {doc.pages === 1 ? "page" : "pages"} · {doc.uploadedAt.toLocaleTimeString()}
                  </p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => setConceptMapDoc(doc)}
                    title="Generate concept map"
                    className="p-1 rounded-lg hover:bg-purple-600/20 text-gray-600 hover:text-purple-400 transition-colors"
                  >
                    <Network className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setCheatSheetDoc(doc)}
                    title="Generate cheat sheet"
                    className="p-1 rounded-lg hover:bg-blue-600/20 text-gray-600 hover:text-blue-400 transition-colors"
                  >
                    <Sparkles className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => onRemove(doc.doc_id)}
                    className="p-1 rounded-lg hover:bg-gray-700 text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>

    {/* Cheat Sheet modal */}
    <AnimatePresence>
      {cheatSheetDoc && (
        <CheatSheet
          docId={cheatSheetDoc.doc_id}
          filename={cheatSheetDoc.filename}
          onClose={() => setCheatSheetDoc(null)}
        />
      )}
    </AnimatePresence>

    {/* Concept Map modal */}
    <AnimatePresence>
      {conceptMapDoc && (
        <ConceptMapModal
          docId={conceptMapDoc.doc_id}
          filename={conceptMapDoc.filename}
          onClose={() => setConceptMapDoc(null)}
        />
      )}
    </AnimatePresence>
    </>
  );
}
