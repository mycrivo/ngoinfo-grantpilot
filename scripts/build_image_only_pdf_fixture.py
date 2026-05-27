#!/usr/bin/env python3
"""Build a minimal image-only PDF (no text layer) for D-039 guard fixtures. Stdlib only."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "docling_intake"
    / "image_only_no_text_layer.pdf"
)

# 1x1 white RGB image stream
IMAGE_HEX = "FFFFFF"


def _build_pdf() -> bytes:
    objects: list[bytes] = []

    def add_obj(body: str) -> int:
        objects.append(body.encode("latin-1"))
        return len(objects)

    catalog = add_obj("<< /Type /Catalog /Pages 2 0 R >>")
    pages = add_obj("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    page = add_obj(
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        "/Resources << /XObject << /Im1 5 0 R >> >> /Contents 4 0 R >>"
    )
    content_stream = b"q 200 0 0 200 0 0 cm /Im1 Do Q"
    contents = add_obj(
        f"<< /Length {len(content_stream)} >>\nstream\n".encode("latin-1").decode()
        + content_stream.decode("latin-1")
        + "\nendstream"
    )
    image = add_obj(
        f"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
        f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Length {len(IMAGE_HEX) // 2} "
        f"/Filter /ASCIIHexDecode >>\nstream\n{IMAGE_HEX}\nendstream"
    )

    parts = [b"%PDF-1.4\n"]
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in parts))
        parts.append(f"{index} 0 obj\n".encode("latin-1"))
        parts.append(body)
        parts.append(b"\nendobj\n")

    xref_offset = sum(len(part) for part in parts)
    parts.append(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    parts.append(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        parts.append(f"{offset:010d} 00000 n \n".encode("latin-1"))
    parts.append(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
    )
    return b"".join(parts)


def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_bytes(_build_pdf())
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
