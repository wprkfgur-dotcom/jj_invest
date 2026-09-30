import os
from PIL import Image

src_path = r"C:\Users\huxley\.gemini\antigravity-ide\brain\5f8f3383-315e-4623-9358-323ea1817703\jj_invest_app_icon_1790761145109.jpg"
src_img = Image.open(src_path).convert("RGBA")

projects = [
    r"C:\ai_development\flet_apk_project\build\flutter",
    r"C:\ai_development\mobile_project\build\flutter"
]

# 1. Update master icon.png (1024x1024)
for proj in projects:
    img_dir = os.path.join(proj, "images")
    if os.path.exists(img_dir):
        src_img.save(os.path.join(img_dir, "icon.png"), "PNG")
        print(f"Saved master icon to {img_dir}\\icon.png")

# 2. Update Android launcher icons
mipmap_sizes = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192
}

drawable_sizes = {
    "drawable-mdpi": 108,
    "drawable-hdpi": 162,
    "drawable-xhdpi": 216,
    "drawable-xxhdpi": 324,
    "drawable-xxxhdpi": 432
}

bg_xml_content = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#01051e</color>
</resources>
"""

for proj in projects:
    res_dir = os.path.join(proj, "android", "app", "src", "main", "res")
    if not os.path.exists(res_dir):
        continue

    # Update ic_launcher_background.xml
    val_dir = os.path.join(res_dir, "values")
    os.makedirs(val_dir, exist_ok=True)
    bg_xml_path = os.path.join(val_dir, "ic_launcher_background.xml")
    with open(bg_xml_path, "w", encoding="utf-8") as f:
        f.write(bg_xml_content)
    print(f"Updated {bg_xml_path}")

    # Update mipmap legacy icons
    for folder, size in mipmap_sizes.items():
        f_dir = os.path.join(res_dir, folder)
        os.makedirs(f_dir, exist_ok=True)
        out_path = os.path.join(f_dir, "ic_launcher.png")
        resized = src_img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(out_path, "PNG")
        print(f"Saved {out_path}")

    # Update drawable foreground icons (centered in safe zone 76%)
    for folder, size in drawable_sizes.items():
        f_dir = os.path.join(res_dir, folder)
        os.makedirs(f_dir, exist_ok=True)
        out_path = os.path.join(f_dir, "ic_launcher_foreground.png")
        fg_canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        inner_size = int(size * 0.76)
        inner_resized = src_img.resize((inner_size, inner_size), Image.Resampling.LANCZOS)
        offset = (size - inner_size) // 2
        fg_canvas.paste(inner_resized, (offset, offset))
        fg_canvas.save(out_path, "PNG")
        print(f"Saved {out_path}")

print("ALL APP ICONS UPDATED SUCCESSFULLY!")
