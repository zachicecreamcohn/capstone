import React, { forwardRef, useCallback, useState, useRef } from 'react';

interface ZoomableContainerProps extends React.HTMLProps<HTMLDivElement> {
  zoom: number;
  onZoomChange: (zoom: number) => void;
  isPanMode: boolean;
}

const ZoomableContainer = forwardRef<HTMLDivElement, ZoomableContainerProps>(
  ({ zoom, onZoomChange, isPanMode, children, ...props }, ref) => {
    const [isPanning, setIsPanning] = useState(false);
    const lastPanPosition = useRef({ x: 0, y: 0 });
    const containerRef = useRef<HTMLDivElement>(null);

    const handleWheel = useCallback(
      (e: React.WheelEvent) => {
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          const container = containerRef.current;
          if (!container) return;

          const rect = container.getBoundingClientRect();
          const contentRect = container.firstElementChild?.getBoundingClientRect();
          if (!contentRect) return;

          // Calculate the center of the viewport
          const viewportCenterX = rect.width / 2;
          const viewportCenterY = rect.height / 2;

          // Calculate current scroll position relative to the content
          const scrollLeft = container.scrollLeft;
          const scrollTop = container.scrollTop;

          // Calculate the point we want to zoom around (relative to content)
          const zoomPointX = scrollLeft + viewportCenterX;
          const zoomPointY = scrollTop + viewportCenterY;

          // Calculate new zoom level
          const delta = -e.deltaY;
          const zoomFactor = delta > 0 ? 1.1 : 0.9;
          const newZoom = Math.min(5, Math.max(0.1, zoom * zoomFactor));

          // Calculate how the content dimensions will change
          const scaleChange = newZoom / zoom;

          // Calculate new scroll position to maintain the same relative position
          const newScrollLeft = zoomPointX * scaleChange - viewportCenterX;
          const newScrollTop = zoomPointY * scaleChange - viewportCenterY;

          onZoomChange(newZoom);

          // Update scroll position after zoom
          requestAnimationFrame(() => {
            if (container) {
              container.scrollLeft = newScrollLeft;
              container.scrollTop = newScrollTop;
            }
          });
        }
      },
      [zoom, onZoomChange]
    );

    const handleMouseDown = useCallback(
      (e: React.MouseEvent) => {
        if (isPanMode && e.button === 0) {
          e.preventDefault();
          setIsPanning(true);
          lastPanPosition.current = { x: e.clientX, y: e.clientY };
          document.body.style.cursor = 'grabbing';
        }
      },
      [isPanMode]
    );

    const handleMouseMove = useCallback(
      (e: React.MouseEvent) => {
        if (isPanning && containerRef.current) {
          e.preventDefault(); // Prevent text selection during pan

          // Calculate the movement delta
          const dx = (e.clientX - lastPanPosition.current.x);
          const dy = (e.clientY - lastPanPosition.current.y);

          // Update scroll position considering zoom level
          containerRef.current.scrollLeft -= dx;
          containerRef.current.scrollTop -= dy;

          // Update last position for next move event
          lastPanPosition.current = { x: e.clientX, y: e.clientY };
        }
      },
      [isPanning]
    );

    const handleMouseUp = useCallback(() => {
      if (isPanning) {
        setIsPanning(false);
        document.body.style.cursor = 'default';
      }
    }, [isPanning]);

    // Clean up event listeners and cursor on unmount
    React.useEffect(() => {
      const cleanup = () => {
        setIsPanning(false);
        document.body.style.cursor = 'default';
      };

      window.addEventListener('mouseup', cleanup);
      return () => {
        window.addEventListener('mouseup', cleanup);
        cleanup();
      };
    }, []);

    return (
      <div
        ref={(node) => {
          if (typeof ref === 'function') {
            ref(node);
          } else if (ref) {
            ref.current = node;
          }
          containerRef.current = node;
        }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{
          maxHeight: '70vh',
          overflow: 'auto',
          cursor: isPanMode ? (isPanning ? 'grabbing' : 'grab') : 'default',
          position: 'relative',
          WebkitUserSelect: 'none',
          userSelect: 'none'
        }}
        {...props}
      >
        <div
          style={{
            transform: `scale(${zoom})`,
            transformOrigin: '0 0',
            width: 'fit-content',
            height: 'fit-content',
            willChange: 'transform' // Optimize performance
          }}
        >
          {children}
        </div>
      </div>
    );
  }
);

ZoomableContainer.displayName = 'ZoomableContainer';

export default ZoomableContainer;
