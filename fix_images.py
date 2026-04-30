"""
هذا السكريبت يُشغَّل مرة واحدة لإصلاح أسماء ملفات الصور
"""
import shutil
import os

images_dir = os.path.join(os.path.dirname(__file__), 'static', 'images')
print(f"مجلد الصور: {images_dir}")
print(f"الملفات الموجودة: {os.listdir(images_dir)}")

# vision2030.png.png -> vision2030.png
src = os.path.join(images_dir, 'vision2030.png.png')
dst = os.path.join(images_dir, 'vision2030.png')
if os.path.exists(src) and not os.path.exists(dst):
    shutil.copy2(src, dst)
    print("✅ vision2030.png تم إنشاؤه")
elif os.path.exists(dst):
    print("ℹ️  vision2030.png موجود مسبقاً")
else:
    print("❌ vision2030.png.png غير موجود!")

# vision20300.png -> jawazat.png
src2 = os.path.join(images_dir, 'vision20300.png')
dst2 = os.path.join(images_dir, 'jawazat.png')
if os.path.exists(src2) and not os.path.exists(dst2):
    shutil.copy2(src2, dst2)
    print("✅ jawazat.png تم إنشاؤه")
elif os.path.exists(dst2):
    print("ℹ️  jawazat.png موجود مسبقاً")
else:
    print("❌ vision20300.png غير موجود!")

print(f"\nالملفات بعد الإصلاح: {os.listdir(images_dir)}")
