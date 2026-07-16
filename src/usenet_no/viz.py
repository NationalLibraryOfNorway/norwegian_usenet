import colorsys


def hsl_to_hex(h, s, lightness):
    r, g, b = colorsys.hls_to_rgb(h / 360, lightness / 100, s / 100)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
