import { useRef, useState } from "react";

import { Button } from "../../../components/ui/button";
import { cn } from "../../../lib/utils";
import { useI18n } from "../../i18n/useI18n";

interface Props {
  disabled?: boolean;
  onSubmit: (file: File) => void;
}

function isJsonFile(file: File): boolean {
  const fileName = file.name.toLowerCase();
  return fileName.endsWith(".json") || file.type.includes("json");
}

export function FileUpload({ disabled, onSubmit }: Props) {
  const { t } = useI18n();
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const applyFile = (file: File | null) => {
    if (!file) {
      return;
    }

    if (!isJsonFile(file)) {
      setSelectedFile(null);
      setFileError(t("analyze.upload.invalid"));
      return;
    }

    setSelectedFile(file);
    setFileError(null);
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-heading text-ink">{t("analyze.upload.title")}</h2>
      <div
        className={cn(
          "rounded-2xl border-2 border-dashed p-6 text-center transition duration-200 md:p-8",
          dragActive && !disabled && "border-[var(--color-accent-strong)] bg-[var(--color-accent-soft)]/40",
          !dragActive && "border-slate-300 bg-slate-50/70",
          disabled && "cursor-not-allowed opacity-60"
        )}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label={t("analyze.upload.aria")}
        onKeyDown={(event) => {
          if (disabled) {
            return;
          }
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) {
            setDragActive(true);
          }
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragActive(false);
          if (disabled) {
            return;
          }
          applyFile(event.dataTransfer.files?.[0] ?? null);
        }}
      >
        <p className="text-sm text-slate-700">{t("analyze.upload.hint")}</p>
        <Button
          variant="ocean"
          className="mt-4"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
          type="button"
        >
          {t("analyze.upload.choose")}
        </Button>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept="application/json,.json"
          disabled={disabled}
          onChange={(event) => applyFile(event.target.files?.[0] ?? null)}
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200/70 bg-white/70 p-3">
        <span className="text-sm text-slate-700">
          {selectedFile ? t("analyze.upload.selected", { name: selectedFile.name }) : t("analyze.upload.none")}
        </span>
        <Button disabled={disabled || !selectedFile} onClick={() => selectedFile && onSubmit(selectedFile)} type="button">
          {t("analyze.upload.start")}
        </Button>
      </div>

      {fileError && <p className="text-sm text-rose-700">{fileError}</p>}
    </div>
  );
}
