import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
from qrcode.image.svg import SvgImage

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader


ERROR_MAP = {
    "L (7%)": ERROR_CORRECT_L,
    "M (15%)": ERROR_CORRECT_M,
    "Q (25%)": ERROR_CORRECT_Q,
    "H (30%)": ERROR_CORRECT_H,
}


def build_qr(data: str, box_size: int, border: int, err_level: int) -> qrcode.QRCode:
    qr = qrcode.QRCode(
        version=None,              # auto-fit
        error_correction=err_level,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr


def save_png(qr: qrcode.QRCode, out_png: str):
    img = qr.make_image(fill_color="black", back_color="white")  # PIL image
    img.save(out_png)


def save_svg(qr: qrcode.QRCode, out_svg: str):
    img = qr.make_image(image_factory=SvgImage)
    # qrcode's SvgImage has save(), but some environments prefer writing bytes
    svg_bytes = img.to_string()
    with open(out_svg, "wb") as f:
        f.write(svg_bytes)


def save_pdf_from_png(out_pdf: str, png_path: str, title: str, qr_size_in: float):
    # Trimmed PDF: just the QR code, no title or full page
    qr_size = qr_size_in * inch
    
    # Set page size to match QR code size
    c = canvas.Canvas(out_pdf, pagesize=(qr_size, qr_size))
    
    # Draw QR code at origin (fills entire page)
    c.drawImage(ImageReader(png_path), 0, 0, width=qr_size, height=qr_size, mask="auto")
    c.showPage()
    c.save()


def sanitize_filename(name: str) -> str:
    bad = '<>:"/\\|?*\n\r\t'
    cleaned = "".join("_" if ch in bad else ch for ch in name).strip()
    return cleaned or "qr_code"


def get_unique_filename(folder: str, base: str, ext: str) -> str:
    """Generate a unique filename by adding (1), (2), etc. if file exists."""
    path = os.path.join(folder, f"{base}{ext}")
    if not os.path.exists(path):
        return path
    
    counter = 1
    while True:
        path = os.path.join(folder, f"{base} ({counter}){ext}")
        if not os.path.exists(path):
            return path
        counter += 1


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Static QR Generator (PNG + SVG + PDF)")
        self.geometry("720x430")
        self.minsize(720, 430)

        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="URL or text to encode (static):").pack(anchor="w")
        self.data_text = tk.Text(root, height=8, wrap="word")
        self.data_text.pack(fill="x", pady=(6, 10))

        # Settings row
        settings = ttk.Frame(root)
        settings.pack(fill="x", pady=(0, 10))

        ttk.Label(settings, text="Error correction:").grid(row=0, column=0, sticky="w")
        self.err_var = tk.StringVar(value="M (15%)")
        ttk.Combobox(settings, textvariable=self.err_var, values=list(ERROR_MAP.keys()),
                     state="readonly", width=12).grid(row=0, column=1, sticky="w", padx=(8, 18))

        ttk.Label(settings, text="Box size:").grid(row=0, column=2, sticky="w")
        self.box_var = tk.StringVar(value="10")
        ttk.Entry(settings, textvariable=self.box_var, width=6).grid(row=0, column=3, sticky="w", padx=(8, 18))

        ttk.Label(settings, text="Border:").grid(row=0, column=4, sticky="w")
        self.border_var = tk.StringVar(value="1")
        ttk.Entry(settings, textvariable=self.border_var, width=6).grid(row=0, column=5, sticky="w", padx=(8, 18))

        ttk.Label(settings, text="PDF QR size (in):").grid(row=0, column=6, sticky="w")
        self.pdfsize_var = tk.StringVar(value="4.0")
        ttk.Entry(settings, textvariable=self.pdfsize_var, width=6).grid(row=0, column=7, sticky="w", padx=(8, 0))

        settings.grid_columnconfigure(8, weight=1)

        # Output folder row
        out = ttk.Frame(root)
        out.pack(fill="x", pady=(0, 8))

        ttk.Label(out, text="Output folder:").pack(side="left")
        self.folder_var = tk.StringVar(value=os.getcwd())
        ttk.Entry(out, textvariable=self.folder_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(out, text="Browse…", command=self.browse_folder).pack(side="left")

        # Base filename row
        fname = ttk.Frame(root)
        fname.pack(fill="x", pady=(0, 10))

        ttk.Label(fname, text="Filename:").pack(side="left")
        self.base_var = tk.StringVar(value="qr_code")
        ttk.Entry(fname, textvariable=self.base_var).pack(side="left", fill="x", expand=True, padx=8)

        # Format checkboxes
        formats = ttk.LabelFrame(root, text="Output formats", padding=10)
        formats.pack(fill="x", pady=(0, 12))

        self.do_png = tk.BooleanVar(value=True)
        self.do_svg = tk.BooleanVar(value=True)
        self.do_pdf = tk.BooleanVar(value=True)

        ttk.Checkbutton(formats, text="PNG", variable=self.do_png).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(formats, text="SVG", variable=self.do_svg).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(formats, text="PDF", variable=self.do_pdf).pack(side="left", padx=(0, 16))

        # Buttons
        btns = ttk.Frame(root)
        btns.pack(fill="x")

        ttk.Button(btns, text="Generate", command=self.generate).pack(side="left")
        ttk.Button(btns, text="Clear", command=self.clear).pack(side="left", padx=10)

        self.status = tk.StringVar(value="Ready.")
        ttk.Label(root, textvariable=self.status, foreground="#444").pack(anchor="w", pady=(6, 0))


    def browse_folder(self):
        path = filedialog.askdirectory(initialdir=self.folder_var.get() or os.getcwd())
        if path:
            self.folder_var.set(path)

    def clear(self):
        self.data_text.delete("1.0", "end")
        self.status.set("Cleared.")

    def generate(self):
        data = self.data_text.get("1.0", "end").strip()
        if not data:
            messagebox.showerror("Missing input", "Enter a URL or text to encode.")
            return

        folder = self.folder_var.get().strip() or os.getcwd()
        if not os.path.isdir(folder):
            messagebox.showerror("Invalid folder", "Output folder does not exist.")
            return

        base = sanitize_filename(self.base_var.get().strip())
        if not (self.do_png.get() or self.do_svg.get() or self.do_pdf.get()):
            messagebox.showerror("No formats selected", "Select at least one output format.")
            return

        try:
            box_size = int(self.box_var.get())
            border = int(self.border_var.get())
            pdf_size_in = float(self.pdfsize_var.get())
            if box_size < 1 or border < 0 or pdf_size_in <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid settings", "Box size must be >= 1, border >= 0, PDF size > 0.")
            return

        err_level = ERROR_MAP[self.err_var.get()]

        try:
            qr = build_qr(data, box_size, border, err_level)

            # Generate unique filenames
            out_png = get_unique_filename(folder, base, ".png")
            out_svg = get_unique_filename(folder, base, ".svg")
            out_pdf = get_unique_filename(folder, base, ".pdf")

            # If PDF is selected, we need PNG anyway (to embed in PDF)
            need_png_for_pdf = self.do_pdf.get()
            made_png = False

            if self.do_png.get() or need_png_for_pdf:
                save_png(qr, out_png)
                made_png = True

            if self.do_svg.get():
                save_svg(qr, out_svg)

            if self.do_pdf.get():
                if not made_png:
                    save_png(qr, out_png)
                save_pdf_from_png(out_pdf, out_png, data, pdf_size_in)

            outputs = []
            if self.do_png.get(): outputs.append(out_png)
            if self.do_svg.get(): outputs.append(out_svg)
            if self.do_pdf.get(): outputs.append(out_pdf)

            self.status.set("Saved:\n" + "\n".join(outputs))
            messagebox.showinfo("Done", "Generated:\n\n" + "\n".join(outputs))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate files:\n{e}")


if __name__ == "__main__":
    App().mainloop()