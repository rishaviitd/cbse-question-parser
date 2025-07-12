from PIL import Image, ImageDraw, ImageFont
from typing import List

def compose_diagram_preview(
    figure_snippets: List[List[Image.Image]],
    dpi: int = 300,
    thumb_width: int = 200,
    font_path: str = None
) -> Image.Image:
    """
    Build a single PIL image that mirrors the Streamlit UI layout:
      - “Here are figures present:” heading
      - For each page:
          - Subheader “Page X”
          - For each figure:
              - Label “Figure Y”
              - Thumbnail image resized to thumb_width
    """
    # Load fonts: H1 (48px bold), H2 (36px bold), H3 (24px regular)
    if font_path:
        try:
            heading_font = ImageFont.truetype(font_path, size=48)
            subheader_font = ImageFont.truetype(font_path, size=36)
            label_font = ImageFont.truetype(font_path, size=24)
        except Exception:
            heading_font = ImageFont.load_default()
            subheader_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
    else:
        # Try common system fonts for bold and regular
        font_bold_candidates = [
            "DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ]
        font_reg_candidates = [
            "DejaVuSans.ttf",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        heading_font = subheader_font = None
        for fb in font_bold_candidates:
            try:
                heading_font = ImageFont.truetype(fb, size=48)
                subheader_font = ImageFont.truetype(fb, size=36)
                break
            except Exception:
                continue
        label_font = None
        for fr in font_reg_candidates:
            try:
                label_font = ImageFont.truetype(fr, size=24)
                break
            except Exception:
                continue
        # Fallback to default bitmap font if any loading failed
        if heading_font is None or subheader_font is None or label_font is None:
            heading_font = ImageFont.load_default()
            subheader_font = ImageFont.load_default()
            label_font = ImageFont.load_default()

    # Layout parameters
    left_margin = 20
    # Increase top margin and vertical padding for better spacing
    top_margin = 30
    v_padding = 20
    heading_text = "Here are figures present:"

    # First pass: calculate canvas size
    # Dummy draw to measure text using textbbox
    dummy_img = Image.new("RGB", (10, 10))
    draw_dummy = ImageDraw.Draw(dummy_img)
    bbox = draw_dummy.textbbox((0, 0), heading_text, font=heading_font)
    h_heading = bbox[3] - bbox[1]
    total_height = top_margin
    total_height += h_heading + v_padding

    fig_counter = 1
    for page_idx, figs in enumerate(figure_snippets):
        if figs:
            page_text = f"Page {page_idx + 1}"
            bbox = draw_dummy.textbbox((0, 0), page_text, font=subheader_font)
            h_page = bbox[3] - bbox[1]
            total_height += h_page + v_padding
            for fig_img in figs:
                fig_label = f"Figure {fig_counter}"
                bbox = draw_dummy.textbbox((0, 0), fig_label, font=label_font)
                h_label = bbox[3] - bbox[1]
                total_height += h_label + v_padding
                # thumbnail height
                orig_w, orig_h = fig_img.size
                scale = thumb_width / orig_w
                thumb_h = int(orig_h * scale)
                total_height += thumb_h + v_padding
                fig_counter += 1
    total_height += top_margin

    # Canvas width and creation
    canvas_width = thumb_width + left_margin * 2
    canvas = Image.new("RGB", (canvas_width, total_height), "white")
    draw = ImageDraw.Draw(canvas)

    # Second pass: render content
    y = top_margin
    # Heading
    draw.text((left_margin, y), heading_text, fill="black", font=heading_font)
    y += h_heading + v_padding

    fig_counter = 1
    for page_idx, figs in enumerate(figure_snippets):
        if figs:
            page_text = f"Page {page_idx + 1}"
            draw.text((left_margin, y), page_text, fill="black", font=subheader_font)
            bbox = draw.textbbox((0, 0), page_text, font=subheader_font)
            h_page = bbox[3] - bbox[1]
            y += h_page + v_padding
            for fig_img in figs:
                fig_label = f"Figure {fig_counter}"
                draw.text((left_margin, y), fig_label, fill="black", font=label_font)
                bbox = draw.textbbox((0, 0), fig_label, font=label_font)
                h_label = bbox[3] - bbox[1]
                y += h_label + v_padding
                # Resize and paste thumbnail
                orig_w, orig_h = fig_img.size
                scale = thumb_width / orig_w
                thumb_h = int(orig_h * scale)
                thumb = fig_img.resize((thumb_width, thumb_h), resample=Image.Resampling.LANCZOS)
                canvas.paste(thumb, (left_margin, y))
                y += thumb_h + v_padding
                fig_counter += 1

    return canvas 