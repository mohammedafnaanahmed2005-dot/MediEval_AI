from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw, ImageFont

NAVY = "#1E3150"
MUTED = "#71829A"
BLUE = "#3984F6"
GREEN = "#39A477"
RED = "#DE6D62"
AMBER = "#E8A443"
SLATE = "#BBC6D4"
TRACK = "#EDF1F6"
WHITE = "#FFFFFF"


def verification_chart(summary: dict[str, int]) -> bytes:
    canvas = Image.new("RGB", (720, 440), WHITE)
    draw = ImageDraw.Draw(canvas)
    _card(draw, (1, 1, 719, 439))
    draw.text((34, 24), "REFERENCE VERIFICATION", font=_font(17, True), fill=MUTED)

    labels = [
        ("Verified", summary.get("verified", 0), GREEN),
        ("Not verified", summary.get("not_verified", 0), RED),
        ("Unscored", summary.get("unscored", 0), SLATE),
    ]
    total = sum(value for _, value, _ in labels)
    if total:
        start = -90
        bounds = (52, 94, 376, 418)
        for _, value, color in labels:
            extent = value / total * 360
            if value:
                draw.pieslice(bounds, start, start + extent, fill=color, outline=WHITE, width=5)
                start += extent
        draw.ellipse((117, 159, 311, 353), fill=WHITE)
        center = str(summary.get("scored", summary.get("verified", 0) + summary.get("not_verified", 0)))
        _center_text(draw, bounds, center, _font(51, True), NAVY, y_offset=-15)
        _center_text(draw, bounds, "SCORED", _font(16, True), MUTED, y_offset=40)
    else:
        draw.ellipse((52, 94, 376, 418), fill=TRACK)
        draw.ellipse((117, 159, 311, 353), fill=WHITE)
        _center_text(draw, (52, 94, 376, 418), "—", _font(54, True), SLATE)

    y = 124
    for label, value, color in labels:
        draw.ellipse((418, y + 3, 436, y + 21), fill=color)
        draw.text((451, y), label, font=_font(22), fill=MUTED)
        draw.text((642, y - 2), str(value), font=_font(27, True), fill=NAVY, anchor="ra")
        y += 78

    if not total:
        draw.text((420, 362), "Reference answers and AI labels are needed", font=_font(15), fill=MUTED)
        draw.text((420, 386), "to score verification.", font=_font(15), fill=MUTED)
    return _png_bytes(canvas)


def metrics_chart(metrics: dict[str, Any]) -> bytes:
    canvas = Image.new("RGB", (900, 440), WHITE)
    draw = ImageDraw.Draw(canvas)
    _card(draw, (1, 1, 899, 439))
    draw.text((34, 24), "EVALUATION PERFORMANCE", font=_font(17, True), fill=MUTED)
    items = [
        ("Accuracy", metrics.get("accuracy"), BLUE),
        ("Precision", metrics.get("precision"), BLUE),
        ("Recall", metrics.get("recall"), BLUE),
        ("F1 score", metrics.get("f1"), BLUE),
        ("Hallucination rate", metrics.get("hallucination_rate"), RED),
    ]
    y = 83
    for label, value, color in items:
        draw.text((36, y), label, font=_font(18), fill=NAVY)
        x1, x2 = 275, 742
        draw.rounded_rectangle((x1, y + 3, x2, y + 23), radius=9, fill=TRACK)
        if value is not None:
            bounded = max(0.0, min(1.0, float(value)))
            if bounded:
                draw.rounded_rectangle((x1, y + 3, x1 + int((x2 - x1) * bounded), y + 23), radius=9, fill=color)
            draw.text((860, y - 3), f"{bounded * 100:.1f}%", font=_font(19, True), fill=NAVY, anchor="ra")
        else:
            draw.text((860, y - 3), "N/A", font=_font(17), fill=SLATE, anchor="ra")
        y += 62

    overall_score = metrics.get("overall_score")
    score_text = "N/A" if overall_score is None else f"{float(overall_score):.1f} / 100"
    draw.rounded_rectangle((35, 382, 865, 425), radius=10, fill="#EFF5FF")
    draw.text((52, 393), "OVERALL SCORE", font=_font(15, True), fill=BLUE)
    draw.text((844, 390), score_text, font=_font(20, True), fill=NAVY, anchor="ra")
    return _png_bytes(canvas)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        ("C:\\Windows\\Fonts\\segoeuib.ttf", "C:\\Windows\\Fonts\\arialbd.ttf")
        if bold
        else ("C:\\Windows\\Fonts\\segoeui.ttf", "C:\\Windows\\Fonts\\arial.ttf")
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _card(draw: ImageDraw.ImageDraw, bounds: tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle(bounds, radius=18, fill=WHITE, outline="#E5EBF3", width=2)


def _center_text(
    draw: ImageDraw.ImageDraw,
    bounds: tuple[int, int, int, int],
    text: str,
    font: ImageFont.ImageFont,
    color: str,
    y_offset: int = 0,
) -> None:
    left, top, right, bottom = bounds
    draw.text(((left + right) / 2, (top + bottom) / 2 + y_offset), text, font=font, fill=color, anchor="mm")


def _png_bytes(image: Image.Image) -> bytes:
    stream = BytesIO()
    image.save(stream, format="PNG", optimize=True)
    return stream.getvalue()
