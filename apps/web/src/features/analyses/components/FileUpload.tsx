import { useRef, useState } from "react";

import { Button } from "../../../components/ui/button";

interface Props {
  disabled?: boolean;
  onSubmit: (file: File) => void;
}

export function FileUpload({ disabled, onSubmit }: Props) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <div className="space-y-4">
      <div
        className={`rounded-2xl border-2 border-dashed p-8 text-center transition ${
          dragActive ? "border-ocean bg-mint/40" : "border-slate-300 bg-sand/60"
        }`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragActive(false);
          setSelectedFile(event.dataTransfer.files?.[0] ?? null);
        }}
      >
        <p className="text-sm text-slate-700">Drag and drop `result.json` here or choose file manually.</p>
        <Button
          variant="ocean"
          className="mt-4"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
          type="button"
        >
          Choose File
        </Button>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept="application/json,.json"
          onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="text-sm text-slate-700">{selectedFile ? selectedFile.name : "No file selected"}</span>
        <Button disabled={disabled || !selectedFile} onClick={() => selectedFile && onSubmit(selectedFile)} type="button">
          Start Analysis
        </Button>
      </div>
    </div>
  );
}
