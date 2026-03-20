"use client";

import { useState, useRef, DragEvent, ChangeEvent } from "react";

interface UploadProps {
  onFileSelect: (file: File) => void;
  isAnalyzing: boolean;
}

export default function Upload({ onFileSelect, isAnalyzing }: UploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelection(files[0]);
    }
  };

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelection(files[0]);
    }
  };

  const handleFileSelection = (file: File) => {
    // Validate file type
    const allowedTypes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ];

    if (!allowedTypes.includes(file.type)) {
      alert("Please upload a PDF or DOCX file only.");
      return;
    }

    // Validate file size (10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      alert("File size must be less than 10MB.");
      return;
    }

    setSelectedFile(file);
  };

  const handleAnalyze = () => {
    if (selectedFile) {
      onFileSelect(selectedFile);
    }
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4 py-12">
      <div className="max-w-2xl w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-navy mb-3">
            Contract Review Assistant
          </h1>
          <p className="text-gray-600">
            Upload your contract for AI-powered analysis and risk assessment
          </p>
        </div>

        {/* Upload Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`
            border-2 border-dashed rounded-lg p-12 text-center transition-all
            ${
              isDragging
                ? "border-accent bg-blue-50"
                : "border-gray-300 hover:border-accent hover:bg-gray-50"
            }
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx"
            onChange={handleFileInputChange}
            className="hidden"
            disabled={isAnalyzing}
          />

          {isAnalyzing ? (
            <div className="space-y-4">
              <div className="flex justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent" />
              </div>
              <p className="text-accent font-medium">Analysing your contract...</p>
              <p className="text-sm text-gray-500">This may take a few moments</p>
            </div>
          ) : selectedFile ? (
            <div className="space-y-4">
              <svg
                className="w-16 h-16 mx-auto text-green-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div>
                <p className="font-medium text-navy mb-1">{selectedFile.name}</p>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <button
                onClick={() => setSelectedFile(null)}
                className="text-sm text-accent hover:underline"
              >
                Choose different file
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <svg
                className="w-16 h-16 mx-auto text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <div>
                <p className="text-gray-700 mb-2">
                  Drag and drop your contract here, or
                </p>
                <button
                  onClick={handleBrowseClick}
                  className="text-accent font-medium hover:underline"
                >
                  browse files
                </button>
              </div>
              <p className="text-sm text-gray-500">Accepts PDF and DOCX files (max 10MB)</p>
            </div>
          )}
        </div>

        {/* Analyze Button */}
        {selectedFile && !isAnalyzing && (
          <div className="mt-6">
            <button
              onClick={handleAnalyze}
              className="w-full bg-accent text-white py-4 px-6 rounded-lg font-semibold text-lg hover:bg-opacity-90 transition-colors"
            >
              Analyse Contract
            </button>
          </div>
        )}

        {/* Disclaimer */}
        <div className="mt-8 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <p className="text-xs text-gray-600 text-center leading-relaxed">
            <strong>Disclaimer:</strong> This tool is for informational purposes only and does not
            constitute legal advice. Always verify outputs with a qualified lawyer.
          </p>
        </div>
      </div>
    </div>
  );
}
