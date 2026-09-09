# import cv2
# from ultralytics import YOLO

# image = cv2.imread('../../data/samples/shelf_01_full.png')

# if image is None:
#     raise RuntimeError('Could not load image')

# model = YOLO('yolo11n.pt')

# results = model.predict(
#     source=image,
#     conf=0.25,
#     device='cpu',
#     verbose=False,
# )

# for result in results:
#     if result.boxes is None:
#         continue

#     for box in result.boxes:
#         class_id = int(box.cls.item())
#         confidence = float(box.conf.item())
#         class_name = model.names[class_id]

#         print(
#             f'class_id={class_id} '
#             f'class={class_name} '
#             f'confidence={confidence:.3f}'
#         )


import cv2

from app.vision.yolo import YOLOStockDetector

image = cv2.imread("../../data/samples/shelf_01_full.png")

if image is None:
    raise RuntimeError("Could not load image")

detector = YOLOStockDetector(
    model_path="yolo11n.pt",
    confidence_threshold=0.1,
    class_ids=[39],
    device="cpu",
)

result = detector.detect(image)

print("Detector:", result.detector_name)
print("Detected units:", result.detected_units)
