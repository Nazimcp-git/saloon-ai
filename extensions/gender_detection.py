"""
Gender Detection Extension (Stub)
===================================
Optional module for detecting gender of detected persons.

STATUS: Stub — not fully implemented.
Design for easy plug-in of a lightweight classifier.

To implement:
    1. Use a lightweight CNN (e.g., MobileNet fine-tuned on gender)
    2. Crop detected person bounding boxes
    3. Classify each crop
    4. Return gender label with confidence

Usage:
    ext = GenderDetection()
    results = ext.process(frame, detections)
"""

import logging

logger = logging.getLogger(__name__)


class GenderDetection:
    """
    Gender detection extension stub.
    
    Designed to be plugged into the main pipeline.
    Follows the standard extension interface.
    """

    def __init__(self, model_path=None):
        """
        Initialize gender detection.

        Args:
            model_path (str, optional): Path to gender classification model.
        """
        self.model_path = model_path
        self._model = None
        self.enabled = False

        logger.info(
            "GenderDetection extension loaded (stub — not implemented). "
            "Set model_path and call load_model() to enable."
        )

    def load_model(self):
        """
        Load the gender classification model.
        
        TODO: Implement with a lightweight classifier.
        Recommended approach:
            - Use OpenCV DNN with a pre-trained Caffe model
            - Or use a MobileNetV2 fine-tuned on gender classification
        """
        logger.warning("GenderDetection.load_model() not implemented.")
        # Example implementation:
        # self._model = cv2.dnn.readNetFromCaffe(prototxt, caffemodel)
        # self.enabled = True

    def process(self, frame, detections):
        """
        Process detections and predict gender.

        Args:
            frame (numpy.ndarray): Current video frame.
            detections (list[tuple]): List of (x1, y1, x2, y2, conf).

        Returns:
            list[dict]: [{"bbox": (x1,y1,x2,y2), "gender": str, "confidence": float}]
                Returns empty list if not implemented.
        """
        if not self.enabled or self._model is None:
            return []

        results = []
        for det in detections:
            x1, y1, x2, y2 = det[:4]
            # TODO: Crop, preprocess, and classify
            results.append({
                "bbox": (x1, y1, x2, y2),
                "gender": "unknown",
                "confidence": 0.0,
            })

        return results
