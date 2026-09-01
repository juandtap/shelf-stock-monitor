from app.vision.models import RegionOfInterest
from app.vision.roi_visualizer import ROIVisualizer

REFERENCE_IMAGE = "../../data/references/shelf_01_empty.png"
OUTPUT_IMAGE = "../../data/generated/shelf_01_rois.png"


def main() -> None:
    image = ROIVisualizer.load(
        REFERENCE_IMAGE,
    )

    height, width = image.shape[:2]

    print(f"Reference image size: {width}x{height}")

    slot_width = width // 4

    horizontal_margin = int(slot_width * 0.05)

    roi_y = int(height * 0.10)
    roi_bottom = int(height * 0.78)
    roi_height = roi_bottom - roi_y

    regions = [
        RegionOfInterest(
            x=(slot_width * index) + horizontal_margin,
            y=roi_y,
            width=slot_width - (horizontal_margin * 2),
            height=roi_height,
        )
        for index in range(4)
    ]

    preview = ROIVisualizer.draw(
        image=image,
        regions=regions,
    )

    ROIVisualizer.save(
        image=preview,
        output_path=OUTPUT_IMAGE,
    )

    print(f"ROI preview saved to: {OUTPUT_IMAGE}")

    for index, region in enumerate(regions, start=1):
        print(
            f"ROI {index}: x={region.x}, y={region.y}, width={region.width}, height={region.height}"
        )


if __name__ == "__main__":
    main()
