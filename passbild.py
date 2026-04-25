import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageOps
import os

TARGET_RATIO = 1.3


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Passbild Editor")

        self.root.minsize(600, 700)

        self.canvas = tk.Canvas(root, width=500, height=650, bg="gray")
        self.canvas.pack()

        bar = tk.Frame(root)
        bar.pack()

        tk.Button(bar, text="📂 Load", command=self.load).pack(side="left")
        tk.Button(bar, text="❌ Close", command=self.close_image).pack(side="left")
        tk.Button(bar, text="↩ Undo", command=self.undo).pack(side="left")
        tk.Button(bar, text="⟳ Reset", command=self.reset_view).pack(side="left")

        tk.Button(bar, text="🔍 +", command=lambda: self.zoom(1.1)).pack(side="left")
        tk.Button(bar, text="🔍 -", command=lambda: self.zoom(0.9)).pack(side="left")
        tk.Button(bar, text="↺", command=self.rotate_left).pack(side="left")
        tk.Button(bar, text="↻", command=self.rotate_right).pack(side="left")
        tk.Button(bar, text="💾 Export", command=self.export).pack(side="left")

        self.base_img = None
        self.img = None
        self.path = None

        self.scale = 1
        self.zoom_level = 1
        self.rotation = 0

        self.offset_x = 0
        self.offset_y = 0

        self.frame_w = 200
        self.frame_h = int(self.frame_w * TARGET_RATIO)
        self.frame_x = 150
        self.frame_y = 200

        self.dragging = False
        self.history = []

        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag_move)

    # ------------------------
    # LOAD / RESET
    # ------------------------

    def load(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png")]
        )
        if not path:
            return

        self.path = path

        img = Image.open(path)
        img = ImageOps.exif_transpose(img)

        self.base_img = img

        self.reset()
        self.apply()

    def reset(self):
        self.zoom_level = 1
        self.rotation = 0
        self.offset_x = 0
        self.offset_y = 0

        self.scale = min(
            500 / self.base_img.width,
            650 / self.base_img.height
        )

    def reset_view(self):
        if not self.base_img:
            return
        self.reset()
        self.apply()

    def close_image(self):
        self.base_img = None
        self.img = None
        self.path = None
        self.canvas.delete("all")

    # ------------------------
    # HISTORY (UNDO)
    # ------------------------

    def save_state(self):
        self.history.append((
            self.offset_x,
            self.offset_y,
            self.zoom_level,
            self.rotation
        ))
        if len(self.history) > 20:
            self.history.pop(0)

    def undo(self):
        if not self.history:
            return

        self.offset_x, self.offset_y, self.zoom_level, self.rotation = self.history.pop()
        self.apply()

    # ------------------------
    # TRANSFORM
    # ------------------------

    def rotate_left(self):
        self.save_state()
        self.rotation = (self.rotation - 90) % 360
        self.apply()

    def rotate_right(self):
        self.save_state()
        self.rotation = (self.rotation + 90) % 360
        self.apply()

    def zoom(self, f):
        self.save_state()
        self.zoom_level *= f
        self.apply()

    def apply(self):
        if not self.base_img:
            return

        img = self.base_img.rotate(-self.rotation, expand=True)

        w = int(img.width * self.scale * self.zoom_level)
        h = int(img.height * self.scale * self.zoom_level)

        self.img = img.resize((w, h))
        self.tk = ImageTk.PhotoImage(self.img)

        self.clamp_offsets()
        self.render()

    # ------------------------
    # DRAGGING (BEGRENZT)
    # ------------------------

    def clamp_offsets(self):
        if not self.img:
            return

        img_w, img_h = self.img.size

        min_x = self.frame_x + self.frame_w - img_w
        max_x = self.frame_x

        min_y = self.frame_y + self.frame_h - img_h
        max_y = self.frame_y

        # Falls Bild kleiner als Frame → zentrieren
        if img_w < self.frame_w:
            self.offset_x = self.frame_x + (self.frame_w - img_w) // 2
        else:
            self.offset_x = max(min(self.offset_x, max_x), min_x)

        if img_h < self.frame_h:
            self.offset_y = self.frame_y + (self.frame_h - img_h) // 2
        else:
            self.offset_y = max(min(self.offset_y, max_y), min_y)

    def start_drag(self, e):
        if not self.img:
            return
        self.save_state()
        self.dragging = True
        self.lx = e.x
        self.ly = e.y

    def drag_move(self, e):
        if not self.dragging:
            return

        dx = e.x - self.lx
        dy = e.y - self.ly

        self.offset_x += dx
        self.offset_y += dy

        self.lx = e.x
        self.ly = e.y

        self.clamp_offsets()
        self.render()

    # ------------------------
    # RENDER
    # ------------------------

    def render(self):
        self.canvas.delete("all")

        if self.img:
            self.canvas.create_image(
                self.offset_x,
                self.offset_y,
                anchor="nw",
                image=self.tk
            )

        self.canvas.create_rectangle(
            self.frame_x,
            self.frame_y,
            self.frame_x + self.frame_w,
            self.frame_y + self.frame_h,
            outline="red",
            width=3
        )

    # ------------------------
    # EXPORT
    # ------------------------

    def export(self):
        if not self.base_img:
            return

        inv = 1 / (self.scale * self.zoom_level)

        ox = int((self.frame_x - self.offset_x) * inv)
        oy = int((self.frame_y - self.offset_y) * inv)

        ow = int(self.frame_w * inv)
        oh = int(self.frame_h * inv)

        img = self.base_img.rotate(-self.rotation, expand=True)
        cropped = img.crop((ox, oy, ox + ow, oy + oh))

        base, _ = os.path.splitext(self.path)
        out = base + "_cropped.jpg"

        cropped.save(out)
        print("✔ saved:", out)


root = tk.Tk()
App(root)
root.mainloop()