"""
Video Stream Module
====================
Unified video source handler for webcam, video files, and RTSP streams.
Wraps OpenCV VideoCapture with frame skipping and metadata access.

Usage:
    stream = VideoStream()
    while stream.is_opened():
        frame = stream.read()
        if frame is not None:
            # process frame
        ...
    stream.release()
"""

import logging
import cv2

import config

logger = logging.getLogger(__name__)


class VideoStream:
    """
    Unified video input handler.

    Supports:
        - Webcam (integer index: 0, 1, ...)
        - Video file (string path)
        - RTSP stream (string URL starting with rtsp://)
    
    Includes built-in frame skipping for performance optimization.
    """

    def __init__(self, source=None, frame_skip=None, resize_width=None):
        """
        Initialize the video stream.

        Args:
            source: Video source — webcam index (int), file path (str),
                or RTSP URL (str). Defaults to config.VIDEO_SOURCE.
            frame_skip (int, optional): Process every Nth frame.
                Defaults to config.FRAME_SKIP.
            resize_width (int, optional): Resize frame width.
                Defaults to config.RESIZE_WIDTH.
        """
        self.source = source if source is not None else config.VIDEO_SOURCE
        self.frame_skip = frame_skip or config.FRAME_SKIP
        self.resize_width = resize_width or config.RESIZE_WIDTH

        # Frame counter for skip logic
        self._frame_count = 0

        # Determine source type for logging
        if isinstance(self.source, int):
            self._source_type = "webcam"
        elif isinstance(self.source, str) and self.source.startswith("rtsp"):
            self._source_type = "rtsp"
        else:
            self._source_type = "file"

        logger.info(
            f"Opening video source: {self.source} (type: {self._source_type})"
        )

        self._cap = cv2.VideoCapture(self.source)

        if not self._cap.isOpened():
            raise RuntimeError(
                f"Failed to open video source: {self.source}. "
                f"Check that the file exists or camera is connected."
            )

        logger.info(
            f"Video stream opened: {self.frame_width}x{self.frame_height} "
            f"@ {self.fps:.1f} FPS"
        )

    @property
    def fps(self):
        """Frames per second of the source."""
        return self._cap.get(cv2.CAP_PROP_FPS) or 30.0

    @property
    def frame_width(self):
        """Original frame width in pixels."""
        return int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def frame_height(self):
        """Original frame height in pixels."""
        return int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    @property
    def total_frames(self):
        """Total frame count (0 for live sources)."""
        count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return count if count > 0 else 0

    def is_opened(self):
        """Check if the video source is still open."""
        return self._cap.isOpened()

    def read(self):
        """
        Read the next frame from the video source.

        Implements frame skipping: returns None for skipped frames.
        Resizes frame if resize_width is configured.

        Returns:
            numpy.ndarray or None: BGR frame, or None if skipped or end of stream.
        """
        success, frame = self._cap.read()

        if not success or frame is None:
            if self._source_type == "rtsp":
                logger.warning("RTSP stream failed to read frame. Attempting to reconnect...")
                self._cap.release()
                import time
                time.sleep(2)
                self._cap = cv2.VideoCapture(self.source)
                if self._cap.isOpened():
                    logger.info("Successfully reconnected to RTSP stream.")
                    success, frame = self._cap.read()
                else:
                    logger.error("Failed to reconnect to RTSP stream.")
                    return None
            
            if not success or frame is None:
                return None

        self._frame_count += 1

        # ── Frame skip logic ──
        if self._frame_count % self.frame_skip != 0:
            return None

        # ── Resize for performance ──
        if self.resize_width and frame.shape[1] != self.resize_width:
            aspect_ratio = frame.shape[0] / frame.shape[1]
            new_height = int(self.resize_width * aspect_ratio)
            frame = cv2.resize(frame, (self.resize_width, new_height))

        return frame

    def read_raw(self):
        """
        Read frame without skipping or resizing.
        Useful for saving original frames.

        Returns:
            tuple: (success: bool, frame: numpy.ndarray or None)
        """
        return self._cap.read()

    def get_frame_count(self):
        """Return the number of frames read so far."""
        return self._frame_count

    def release(self):
        """Release the video source and free resources."""
        if self._cap is not None:
            self._cap.release()
            logger.info("Video stream released.")

    def get_info(self):
        """Return metadata about the video source."""
        return {
            "source": str(self.source),
            "type": self._source_type,
            "resolution": f"{self.frame_width}x{self.frame_height}",
            "fps": round(self.fps, 1),
            "total_frames": self.total_frames,
            "frame_skip": self.frame_skip,
            "resize_width": self.resize_width,
        }

    def __del__(self):
        """Ensure resources are freed on garbage collection."""
        self.release()
