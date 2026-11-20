import os
import math

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import jdatetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_PATH = os.path.join(BASE_DIR, "template.png")
FONT_PATH = os.path.join(BASE_DIR, "Vazirmatn-RD-Bold.ttf")
OUTPUT_PATH = os.path.join(BASE_DIR, "report.png")

MAX_STATIONS = 25

# رنگ‌ها
BLUE = "#0876B9"
DARK_BLUE = "#123653"
GRID_COLOR = "#B7C9DA"
WHITE = "#FFFFFF"


# ==================================================
# 2. اطلاعات گزارش
# ==================================================
def do_rain(stations):
    # ==================================================
    # 1. تنظیمات اولیه
    # ==================================================

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    TEMPLATE_PATH = os.path.join(BASE_DIR, "template.png")
    FONT_PATH = os.path.join(BASE_DIR, "Vazirmatn-RD-Bold.ttf")
    OUTPUT_PATH = os.path.join(BASE_DIR, "report.png")

    MAX_STATIONS = 25

    # رنگ‌ها
    BLUE = "#0876B9"
    DARK_BLUE = "#123653"
    GRID_COLOR = "#B7C9DA"
    WHITE = "#FFFFFF"

    # ==================================================
    # 3. بررسی داده‌ها
    # ==================================================

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError("فایل template.png پیدا نشد.")

    if not os.path.exists(FONT_PATH):
        raise FileNotFoundError("فایل فونت پیدا نشد.")

    if not stations:
        raise ValueError("هیچ ایستگاهی برای نمایش وجود ندارد.")

    if len(stations) > MAX_STATIONS:
        raise ValueError(f"حداکثر {MAX_STATIONS} ایستگاه قابل نمایش است.")

    for station in stations:
        if float(station["rain"]) < 0:
            raise ValueError("مقدار بارش نمی‌تواند منفی باشد.")


    # ==================================================
    # 4. توابع کمکی
    # ==================================================

    def fa(text):
        """آماده‌سازی متن فارسی برای Pillow"""

        return get_display(
            arabic_reshaper.reshape(str(text))
        )


    def fa_num(value):
        """تبدیل اعداد انگلیسی به فارسی"""

        return str(value).translate(
            str.maketrans(
                "0123456789",
                "۰۱۲۳۴۵۶۷۸۹"
            )
        )


    def load_font(size):
        return ImageFont.truetype(FONT_PATH, size)


    def nice_ceiling(value):
        """تعیین سقف مناسب محور عمودی"""

        if value <= 0:
            return 1

        power = 10 ** math.floor(math.log10(value))
        normalized = value / power

        for step in [1, 2, 2.5, 5, 10]:
            if normalized <= step:
                return step * power

        return 10 * power


    def draw_centered_text(draw, position, text, font, fill):
        """نوشتن متن با مرکزیت مشخص"""

        draw.text(
            position,
            text,
            font=font,
            fill=fill,
            anchor="mm"
        )


    # ==================================================
    # 5. بارگذاری تصویر و فونت
    # ==================================================

    img = Image.open(TEMPLATE_PATH).convert("RGB")
    draw = ImageDraw.Draw(img)

    width, height = img.size

    # فونت‌های عمومی
    title_font = load_font(25)
    small_font = load_font(21)
    value_font = load_font(24)


    # ==================================================
    # 6. درج تاریخ و ساعت
    # ==================================================

    now = jdatetime.datetime.now()

    date = fa_num(now.strftime("%Y/%m/%d"))
    time = fa_num(now.strftime("%H:%M"))

    draw_centered_text(
        draw,
        (790, 231),
        fa(date),
        small_font,
        DARK_BLUE
    )

    draw_centered_text(
        draw,
        (800, 301),
        fa(time),
        small_font,
        DARK_BLUE
    )


    # ==================================================
    # 7. محاسبات آماری
    # ==================================================

    total_rain = sum(float(s["rain"]) for s in stations)

    wettest = max(
        stations,
        key=lambda s: float(s["rain"])
    )

    driest = min(
        stations,
        key=lambda s: float(s["rain"])
    )

    max_rain = max(float(s["rain"]) for s in stations)


    # ==================================================
    # 8. تنظیمات داینامیک نمودار
    # ==================================================

    count = len(stations)

    # محدوده نمودار
    chart_left = 105
    chart_right = 1040

    chart_top = 560
    chart_bottom = 900

    chart_width = chart_right - chart_left
    chart_height = chart_bottom - chart_top

    # فاصله اختصاص یافته به هر ایستگاه
    slot_width = chart_width / count

    # عرض ستون متناسب با تعداد ایستگاه‌ها
    bar_width = max(
        8,
        min(70, slot_width * 0.62)
    )

    # تعیین اندازه فونت بر اساس تعداد ایستگاه‌ها
    if count <= 6:

        station_font = load_font(21)
        value_font = load_font(23)

    elif count <= 12:

        station_font = load_font(17)
        value_font = load_font(18)

    elif count <= 18:

        station_font = load_font(14)
        value_font = load_font(15)

    else:

        station_font = load_font(15)
        value_font = load_font(14)


    # ==================================================
    # 9. تعیین مقیاس محور عمودی
    # ==================================================

    axis_max = nice_ceiling(max_rain * 1.2)

    # تعداد تقسیمات محور
    tick_count = 5

    tick_step = axis_max / tick_count


    # ==================================================
    # 10. رسم خطوط و اعداد محور
    # ==================================================

    axis_font = load_font(16)

    for i in range(tick_count + 1):

        value = tick_step * i

        y = chart_bottom - (
            value / axis_max
        ) * chart_height

        # خطوط راهنمای افقی
        draw.line(
            (
                chart_left,
                int(y),
                chart_right,
                int(y)
            ),
            fill=GRID_COLOR,
            width=2 if i == 0 else 1
        )

        # اعداد محور
        label = (
            str(int(value))
            if value.is_integer()
            else f"{value:g}"
        )

        draw.text(
            (chart_left - 15, y),
            fa_num(label),
            font=axis_font,
            fill=DARK_BLUE,
            anchor="rm"
        )


    # ==================================================
    # 11. رسم ستون‌ها و نام ایستگاه‌ها
    # ==================================================

    for i, station in enumerate(stations):

        rain = float(station["rain"])

        # مرکز ستون
        center_x = chart_left + slot_width * (i + 0.5)

        # محاسبه ارتفاع ستون
        bar_height = (
            rain / axis_max
        ) * chart_height

        top_y = chart_bottom - bar_height

        # رسم ستون
        draw.rounded_rectangle(
            (
                int(center_x - bar_width / 2),
                int(top_y),
                int(center_x + bar_width / 2),
                chart_bottom
            ),
            radius=8,
            fill=BLUE
        )

        # مقدار بارش بالای ستون
        rain_label = f"{rain:g}"

        draw.text(
            (center_x, top_y - 9),
            rain_label,
            font=value_font,
            fill=DARK_BLUE,
            anchor="ms"
        )

        # نام ایستگاه
        station_name = fa(station["name"] if station["name"] != "ساری-فرودگاه دشت ناز" else "فرودگاه دشت ناز")

        if count <= 6:

            # تعداد کم: نام افقی
            draw_centered_text(
                draw,
                (center_x, 930),
                station_name,
                station_font,
                DARK_BLUE
            )

        else:

            # تعداد زیاد: نام عمودی
            bbox = station_font.getbbox(station_name)

            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            label_img = Image.new(
                "RGBA",
                (
                    text_width + 12,
                    text_height + 12
                ),
                (255, 255, 255, 0)
            )

            label_draw = ImageDraw.Draw(label_img)

            label_draw.text(
                (6 - bbox[0], 6 - bbox[1]),
                station_name,
                font=station_font,
                fill=DARK_BLUE
            )

            label_img = label_img.rotate(
                90,
                expand=True,
                resample=Image.Resampling.BICUBIC
            )

            paste_x = int(
                center_x - label_img.width / 2
            )

            paste_y = 910

            img.paste(
                label_img,
                (paste_x, paste_y),
                label_img
            )


    # ==================================================
    # 12. کارت کم‌بارش‌ترین ایستگاه
    # ==================================================

    draw_centered_text(
        draw,
        (200, 1135),
        fa(driest["name"]),
        load_font(27),
        DARK_BLUE
    )

    draw_centered_text(
        draw,
        (200, 1170),
        f"{fa_num(driest['rain'])} mm",
        small_font,
        BLUE
    )


    # ==================================================
    # 13. کارت پربارش‌ترین ایستگاه
    # ==================================================

    draw_centered_text(
        draw,
        (555, 1135),
        fa(wettest["name"]),
        load_font(27),
        DARK_BLUE
    )

    draw_centered_text(
        draw,
        (555, 1170),
        f"{fa_num(wettest['rain'])} mm",
        small_font,
        BLUE
    )


    # ==================================================
    # 14. کارت مجموع بارش
    # ==================================================

    draw_centered_text(
        draw,
        (925, 1145),
        f"{fa_num(f'{total_rain:.1f}')} mm",
        title_font,
        BLUE
    )


    # ==================================================
    # 15. ذخیره خروجی
    # ==================================================

    return img
    img.save(
        OUTPUT_PATH,
        format="PNG",
        optimize=True
    )

