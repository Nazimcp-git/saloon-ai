"""
Face Recognition Extension (Stub)
====================================
Optional module for identifying known faces among detected persons.

STATUS: Stub — not fully implemented.
Designed for easy integration with the face_recognition library.

To implement:
    1. pip install face_recognition
    2. Encode known faces from a directory of images
    3. Compare detected faces against known encodings

Usage:
    ext = FaceRecognition(known_faces_dir="known_faces/")
    results = ext.process(frame, detections)
"""

import logging

logger = logging.getLogger(__name__)


class FaceRecognition:
    """
    Face recognition extension stub.
    
    Designed for integration with the `face_recognition` library
    or similar lightweight face identification systems.
    """

    def __init__(self, known_faces_dir=None):
        """
        Initialize face recognition.

        Args:
            known_faces_dir (str, optional): Directory containing
                subdirectories of known face images, organized by name.
        """
        self.known_faces_dir = known_faces_dir
        self._known_encodings = {}
        self.enabled = False

        logger.info(
            "FaceRecognition extension loaded (stub — not implemented). "
            "Call load_known_faces() to enable."
        )

    def load_known_faces(self):
        """
        Load and encode known faces from the directory.

        TODO: Implement with face_recognition library.
        Expected directory structure:
            known_faces/
                person_name/
                    photo1.jpg
                    photo2.jpg
        """
        logger.warning("FaceRecognition.load_known_faces() not implemented.")
        # Example implementation:
        # import face_recognition
        # for person_dir in os.listdir(self.known_faces_dir):
        #     for img_file in os.listdir(person_dir):
        #         image = face_recognition.load_image_file(img_path)
        #         encoding = face_recognition.face_encodings(image)[0]
        #         self._known_encodings[person_name] = encoding
        # self.enabled = True

    def process(self, frame, detections):
        """
        Identify known faces in the frame.

        Args:
            frame (numpy.ndarray): Current video frame.
            detections (list[tuple]): List of (x1, y1, x2, y2, conf).

        Returns:
            list[dict]: [{"bbox": ..., "name": str, "confidence": float}]
                Returns empty list if not implemented.
        """
        if not self.enabled:
            return []

        results = []
        for det in detections:
            results.append({
                "bbox": det[:4],
                "name": "unknown",
                "confidence": 0.0,
            })

        return results
