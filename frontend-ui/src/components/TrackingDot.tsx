import React, { useRef, useEffect } from 'react';
import { Target } from 'lucide-react';
import { TrackingPoint } from '../types';

interface TrackingDotProps {
  point: TrackingPoint;
  zoom: number;
  containerRef: React.RefObject<HTMLDivElement>;
  onPositionUpdate?: (id: number, x: number, y: number) => void;
}

const TrackingDot: React.FC<TrackingDotProps> = ({
  point,
  zoom,
  containerRef,
  onPositionUpdate,
}) => {
  const dotRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  useEffect(() => {
    if (!onPositionUpdate) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current || !containerRef.current) return;

      const container = containerRef.current.getBoundingClientRect();
      const scrollLeft = containerRef.current.scrollLeft;
      const scrollTop = containerRef.current.scrollTop;

      const x = (e.clientX - container.left + scrollLeft) / zoom;
      const y = (e.clientY - container.top + scrollTop) / zoom;

      const boundedX = Math.max(0, Math.min(x, container.width / zoom));
      const boundedY = Math.max(0, Math.min(y, container.height / zoom));

      onPositionUpdate(point.id, boundedX, boundedY);
    };

    const handleMouseUp = () => {
      isDragging.current = false;
      document.body.style.cursor = 'default';
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [point.id, zoom, onPositionUpdate]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!onPositionUpdate) return;
    e.preventDefault();
    e.stopPropagation();
    isDragging.current = true;
    document.body.style.cursor = 'move';
  };

  return (
    <div
      ref={dotRef}
      className="absolute cursor-move"
      style={{
        left: `${point.x}px`,
        top: `${point.y}px`,
        transform: 'translate(-50%, -50%)',
        pointerEvents: onPositionUpdate ? 'auto' : 'none'
      }}
      onMouseDown={handleMouseDown}
    >
      <div className="relative group">
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-bold text-white z-10">
            {point.id}
          </span>
        </div>
        <Target className="w-8 h-8 text-indigo-600 drop-shadow-md" />
        <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs py-1 px-2 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
          x: {Math.round(point.x)}, y: {Math.round(point.y)}
        </div>
      </div>
    </div>
  );
};

export default TrackingDot;
