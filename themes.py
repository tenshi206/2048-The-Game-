"""Готовые оформления. Покупки меняют только внешний вид игры."""

THEMES = {
    "classic": {
        "title": "Классика", "price": 0,
        "description": "Тёплое поле и мягкие янтарные оттенки.",
        "background": "#f7f3ec", "text": "#40372f", "muted": "#76695d",
        "board": "#b7a99b", "empty": "#cbbfb2", "card": "#e9e0d5",
        "tile_dark": "#40372f", "tile_light": "#fffaf1",
        "tiles": {
            2: "#eee5d8", 4: "#ead8b7", 8: "#edb277", 16: "#e99059",
            32: "#cf6245", 64: "#c24b36", 128: "#94701e", 256: "#85641c",
            512: "#785719", 1024: "#6c4e19", 2048: "#604515",
        },
    },
    "polar": {
        "title": "Полярная ночь", "price": 60,
        "description": "Глубокое синее поле и холодные оттенки льда.",
        "background": "#101b2b", "text": "#f1f6fd", "muted": "#afc2d7",
        "board": "#263b52", "empty": "#334a62", "card": "#1c2d43",
        "tile_dark": "#10283a", "tile_light": "#f3fbff",
        "tiles": {
            2: "#b9cddb", 4: "#a0c3d5", 8: "#3d7693", 16: "#326785",
            32: "#305a84", 64: "#404f8c", 128: "#216c79", 256: "#205e70",
            512: "#264f69", 1024: "#32426c", 2048: "#483c72",
        },
    },
    "neon": {
        "title": "Неон", "price": 100,
        "description": "Фиолетовый графит, бирюза и розовые акценты.",
        "background": "#161422", "text": "#fff0ff", "muted": "#c4b6d6",
        "board": "#332b46", "empty": "#453b59", "card": "#292236",
        "tile_dark": "#2b2039", "tile_light": "#fff6ff",
        "tiles": {
            2: "#e6d6f2", 4: "#b6e8ed", 8: "#345b69", 16: "#4b457c",
            32: "#714477", 64: "#8a3a68", 128: "#146d67", 256: "#31578b",
            512: "#603f86", 1024: "#7c326d", 2048: "#88402c",
        },
    },
    "obsidian": {
        "title": "Обсидиан", "price": 140,
        "description": "Тёмный камень, медь и старое золото.",
        "background": "#191713", "text": "#fff1d6", "muted": "#c8b795",
        "board": "#42382e", "empty": "#54483b", "card": "#30291f",
        "tile_dark": "#33281c", "tile_light": "#fff4de",
        "tiles": {
            2: "#e7d9bd", 4: "#d8bd88", 8: "#88582e", 16: "#84492c",
            32: "#854032", 64: "#79362c", 128: "#82611f", 256: "#76541b",
            512: "#694519", 1024: "#5b381a", 2048: "#704923",
        },
    },
}


def tile_text_color(theme, value):
    """Выбирает более контрастную надпись для конкретного цвета плитки."""
    background = theme["tiles"].get(value, theme["tiles"][2048])

    def luminance(color):
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [channel / 12.92 if channel <= 0.04045
                  else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
        return sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    base = luminance(background)

    def contrast(color):
        ink = luminance(color)
        return (max(ink, base) + 0.05) / (min(ink, base) + 0.05)

    return max((theme["tile_dark"], theme["tile_light"]), key=contrast)
