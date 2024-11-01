import React, { useCallback } from 'react';
import { Upload } from 'lucide-react';

interface ImageDropzoneProps {
  onImageUpload: (file: File) => void;
}

const ImageDropzone: React.FC<ImageDropzoneProps> = ({ onImageUpload }) => {
  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith('image/')) {
        onImageUpload(file);
      }
    },
    [onImageUpload]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onImageUpload(file);
    }
  };

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-indigo-500 transition-colors cursor-pointer"
    >
      <input
        type="file"
        accept="image/*"
        onChange={handleChange}
        className="hidden"
        id="image-upload"
      />
      <label
        htmlFor="image-upload"
        className="cursor-pointer flex flex-col items-center gap-4"
      >
        <Upload className="w-12 h-12 text-gray-400" />
        <div className="space-y-2">
          <p className="text-lg font-medium text-gray-700">
            Drop your image here, or click to select
          </p>
          <p className="text-sm text-gray-500">
            Supports: JPG, PNG, GIF (Max 10MB)
          </p>
        </div>
      </label>
    </div>
  );
}

export default ImageDropzone;
