import React, { useState, useRef } from 'react';
import { Target, Upload, ZoomIn, ZoomOut, RotateCcw, Move } from 'lucide-react';
import { TrackingPoint } from './types';
import ImageDropzone from './components/ImageDropzone';
import TrackingDot from './components/TrackingDot';
import ZoomableContainer from './components/ZoomableContainer';

function App() {
  const [image, setImage] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [isPanMode, setIsPanMode] = useState(false);
  const [trackingPoints, setTrackingPoints] = useState<TrackingPoint[]>([
    { id: 1, x: 50, y: 50 },
    { id: 2, x: 150, y: 50 },
    { id: 3, x: 50, y: 150 },
    { id: 4, x: 150, y: 150 },
  ]);
  const imageContainerRef = useRef<HTMLDivElement>(null);

  const handleImageUpload = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      setImage(e.target?.result as string);
      setZoom(1);
      setIsPanMode(false);
    };
    reader.readAsDataURL(file);
  };

  const updatePointPosition = (id: number, x: number, y: number) => {
    setTrackingPoints((prev) =>
      prev.map((point) =>
        point.id === id ? { ...point, x, y } : point
      )
    );
  };

  const handleZoomChange = (newZoom: number) => {
    setZoom(newZoom);
  };

  const resetZoom = () => {
    setZoom(1);
    if (imageContainerRef.current) {
      imageContainerRef.current.scrollLeft = 0;
      imageContainerRef.current.scrollTop = 0;
    }
  };

  const togglePanMode = () => {
    setIsPanMode(!isPanMode);
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-6 space-y-6">
          <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-2">
            <Target className="w-8 h-8 text-indigo-600" />
            Image Tracking Points Editor
          </h1>

          {!image ? (
            <ImageDropzone onImageUpload={handleImageUpload} />
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <button
                  onClick={() => handleZoomChange(Math.max(0.1, zoom / 1.1))}
                  className="p-2 rounded-lg hover:bg-gray-100 text-gray-700 transition-colors"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-5 h-5" />
                </button>
                <div className="bg-gray-100 px-3 py-1 rounded-md text-sm font-medium text-gray-700">
                  {Math.round(zoom * 100)}%
                </div>
                <button
                  onClick={() => handleZoomChange(Math.min(5, zoom * 1.1))}
                  className="p-2 rounded-lg hover:bg-gray-100 text-gray-700 transition-colors"
                  title="Zoom In"
                >
                  <ZoomIn className="w-5 h-5" />
                </button>
                <button
                  onClick={resetZoom}
                  className="p-2 rounded-lg hover:bg-gray-100 text-gray-700 transition-colors"
                  title="Reset Zoom"
                >
                  <RotateCcw className="w-5 h-5" />
                </button>
                <div className="w-px h-6 bg-gray-200 mx-1" />
                <button
                  onClick={togglePanMode}
                  className={`p-2 rounded-lg hover:bg-gray-100 transition-colors ${
                    isPanMode ? 'bg-indigo-100 text-indigo-600' : 'text-gray-700'
                  }`}
                  title={isPanMode ? 'Exit Pan Mode' : 'Enter Pan Mode'}
                >
                  <Move className="w-5 h-5" />
                </button>
              </div>

              <ZoomableContainer
                zoom={zoom}
                onZoomChange={handleZoomChange}
                isPanMode={isPanMode}
                className="relative border-2 border-gray-200 rounded-lg overflow-hidden bg-gray-50"
                ref={imageContainerRef}
              >
                <div className="relative">
                  <img
                    src={image}
                    alt="Uploaded"
                    className="max-w-full h-auto"
                    draggable={false}
                  />
                  {trackingPoints.map((point) => (
                    <TrackingDot
                      key={point.id}
                      point={point}
                      zoom={zoom}
                      containerRef={imageContainerRef}
                      onPositionUpdate={!isPanMode ? updatePointPosition : undefined}
                    />
                  ))}
                </div>
              </ZoomableContainer>

              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-700 mb-2">Tracking Points</h3>
                <div className="grid grid-cols-2 gap-4">
                  {trackingPoints.map((point) => (
                    <div key={point.id} className="flex items-center space-x-2 text-sm text-gray-600">
                      <div className="relative w-4 h-4">
                        <Target className="w-4 h-4 text-indigo-600" />
                        <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white">
                          {point.id}
                        </span>
                      </div>
                      <span>Point {point.id}:</span>
                      <span className="font-mono">
                        x: {Math.round(point.x)}, y: {Math.round(point.y)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={() => setImage(null)}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg text-gray-700 transition-colors flex items-center gap-2"
              >
                <Upload className="w-4 h-4" />
                Upload New Image
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
