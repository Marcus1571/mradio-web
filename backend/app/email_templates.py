"""HTML bodies for outbound transactional email — password reset and the
new-account welcome/invite. Table-based, inline-styled markup only (no
external stylesheet, no flexbox/grid, no CSS custom properties): this is
rendered by real email clients, not a browser, and Outlook's Word-based
engine and Gmail's stylesheet stripping rule out anything else. Colors
are the app's own light-theme tokens (frontend/src/index.css), converted
from OKLCH to hex by hand since email clients don't parse oklch().

Hallmark · macrostructure: single-column centered card (email genre) ·
theme: mradio-web light (paper #f4f1ed, ink #181d26, teal accent
#008c92, Newsreader-style serif headline / system sans body) · logo:
recreation of the favicon's arrow mark, gradient fill + hairline stroke
+ drop shadow for real dimensionality (the original's feGaussianBlur/
mask layers don't render reliably in email clients, and a flat single
fill read as a sticker rather than a mark)."""

_PAPER = "#f4f1ed"
_PAPER_2 = "#eae8e3"
_INK = "#181d26"
_INK_2 = "#484d55"
_INK_3 = "#767b82"
_LINE = "#cdcac3"
_ACCENT = "#008c92"
_ACCENT_INK = "#031a1b"

_FONT_DISPLAY = "Georgia, 'Times New Roman', serif"
_FONT_BODY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

# Recreation of favicon.svg's outer silhouette, with its own gradient
# fill + hairline dark stroke + drop shadow baked into a raster PNG
# (not the original's feGaussianBlur/mask/glow layers, which don't
# render reliably across email clients, and not a flat single fill
# either — a first pass at flat teal read as a sticker; a gradient +
# stroke + shadow gives it real material presence instead, per a user
# reference of a similarly-dimensional logo mockup). Shipped as a real
# PNG (frontend/public/email-logo.png, built into frontend/dist and
# served by the app's own static mount) referenced by absolute URL —
# NOT inline <svg>: Outlook desktop's Word-based rendering engine
# doesn't render inline SVG at all, only Gmail/Apple Mail/modern
# webmail do, confirmed via research before choosing this over the
# simpler inline-SVG approach the first draft used.
def _logo_img(base_url: str) -> str:
    # 76x73 display size (~35% up from the original 56x54) — still well
    # within the underlying PNG's native 112x108 (2x) resolution, so
    # the increase doesn't need a re-export at higher DPI.
    src = f"{base_url}/email-logo.png" if base_url else "email-logo.png"
    return (f'<img src="{src}" width="76" height="73" alt="mradio web" '
            'style="display:block; border:0; outline:none;">')


def _shell(preheader: str, content_html: str, base_url: str) -> str:
    """Wraps a card of content in the outer document — light page
    background, centered 480px card, logo header, shared footer. Every
    color is an inline hex (no var()/oklch()); every layout is a table
    (no flex/grid) — both are hard requirements for Outlook's Word
    rendering engine, not a style preference."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<meta name="supported-color-schemes" content="dark light">
<title></title>
</head>
<body style="margin:0; padding:0; background-color:{_PAPER}; font-family:{_FONT_BODY};">
<div style="display:none; max-height:0; overflow:hidden; opacity:0; mso-hide:all;">
{preheader}&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;&#8203;
</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{_PAPER};">
<tr><td align="center" style="padding:48px 20px;">
<table role="presentation" width="480" cellpadding="0" cellspacing="0" border="0" style="max-width:480px; width:100%;">
<tr><td align="center" style="padding-bottom:28px;">
{_logo_img(base_url)}
</td></tr>
<tr><td style="background-color:{_PAPER_2}; border:1px solid {_LINE}; border-radius:16px; padding:40px 36px;">
{content_html}
</td></tr>
<tr><td align="center" style="padding-top:28px;">
<p style="margin:0; font-family:{_FONT_BODY}; font-size:13px; line-height:1.6; color:{_INK_3};">
mradio web &mdash; your own station, wherever you host it.
</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _button(label: str, href: str) -> str:
    return f"""<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:32px 0;">
<tr><td align="center" bgcolor="{_ACCENT}" style="border-radius:10px;">
<a href="{href}" target="_blank" style="display:inline-block; padding:14px 28px; font-family:{_FONT_BODY}; font-size:15px; font-weight:600; color:{_ACCENT_INK}; text-decoration:none; border-radius:10px;">
{label}
</a>
</td></tr>
</table>"""


def _username_line(username: str) -> str:
    """Shown in both emails so a "forgot password" moment can double as
    a "forgot username" recovery — the recipient sees their own username
    plainly stated regardless of which link they clicked."""
    return (f'<p style="margin:0 0 20px; font-family:{_FONT_BODY}; font-size:14px; '
            f'line-height:1.6; color:{_INK_2};">Your username is '
            f'<strong style="color:{_INK};">{username}</strong>.</p>')


def _fallback_link(href: str) -> str:
    return f"""<p style="margin:0 0 4px; font-family:{_FONT_BODY}; font-size:13px; color:{_INK_3};">
If the button doesn&rsquo;t work, copy and paste this link:
</p>
<p style="margin:0; font-family:{_FONT_BODY}; font-size:13px; word-break:break-all;">
<a href="{href}" target="_blank" style="color:{_ACCENT};">{href}</a>
</p>"""


def _origin_of(link: str) -> str:
    """Pulls the scheme+host back out of a full reset/invite link
    (which is always `{base_url}/reset-password?token=...`) so the
    logo's <img src> can be built without every caller needing to pass
    base_url separately — one less thing to get wrong at the call site."""
    if "://" not in link:
        return ""
    scheme, _, rest = link.partition("://")
    host = rest.split("/", 1)[0]
    return f"{scheme}://{host}"


def password_reset_html(link: str, username: str) -> str:
    """Calm and factual on purpose — no charm, no exclamation marks: a
    forgot-password moment is a frustration path (copy.md explicitly
    bans humor there), not an occasion for personality. Always states
    the username plainly — this email doubles as a "forgot my username"
    recovery, since remembering the password but not the username is a
    real, common case, and there's no separate flow for it."""
    content = f"""
<h1 style="margin:0 0 16px; font-family:{_FONT_DISPLAY}; font-size:24px; font-weight:400; color:{_INK}; line-height:1.3;">
Reset your password
</h1>
{_username_line(username)}
<p style="margin:0; font-family:{_FONT_BODY}; font-size:15px; line-height:1.6; color:{_INK_2};">
Someone requested a password reset for your mradio web account. If that was you, set a new password below.
</p>
{_button('Reset password', link)}
<p style="margin:0 0 24px; font-family:{_FONT_BODY}; font-size:13px; line-height:1.6; color:{_INK_3};">
This link expires in 1 hour and can only be used once. If you didn&rsquo;t request this, you can ignore this email &mdash; your password won&rsquo;t change.
</p>
<hr style="border:none; border-top:1px solid {_LINE}; margin:0 0 24px;">
{_fallback_link(link)}
"""
    return _shell("Reset your mradio web password", content, _origin_of(link))


def welcome_html(full_name_or_username: str, username: str, link: str) -> str:
    """The one email in this app that's allowed real warmth — an
    invitation, not a transaction. "Someone wonderful has invited
    you..." is the Plex-style heading the user specifically asked for.
    `full_name_or_username` is used for the greeting (may be a display
    name); `username` is the actual login username, always stated
    separately since the two can differ — the invited person needs to
    know exactly what to type at the login screen later."""
    content = f"""
<p style="margin:0 0 4px; font-family:{_FONT_BODY}; font-size:13px; font-weight:600; letter-spacing:0.02em; text-transform:uppercase; color:{_ACCENT};">
You&rsquo;re invited
</p>
<h1 style="margin:0 0 16px; font-family:{_FONT_DISPLAY}; font-size:26px; font-weight:400; color:{_INK}; line-height:1.3;">
Someone wonderful has invited you to mradio web
</h1>
<p style="margin:0 0 12px; font-family:{_FONT_BODY}; font-size:15px; line-height:1.6; color:{_INK_2};">
Hi {full_name_or_username},
</p>
<p style="margin:0 0 12px; font-family:{_FONT_BODY}; font-size:15px; line-height:1.6; color:{_INK_2};">
You&rsquo;ve got an account on mradio web &mdash; a self-hosted radio player with live now-playing details and AI-written liner notes for whatever&rsquo;s on. Set your password and you&rsquo;re in.
</p>
{_username_line(username)}
{_button('Set your password', link)}
<p style="margin:0 0 24px; font-family:{_FONT_BODY}; font-size:13px; line-height:1.6; color:{_INK_3};">
This link expires in 7 days and can only be used once.
</p>
<hr style="border:none; border-top:1px solid {_LINE}; margin:0 0 24px;">
{_fallback_link(link)}
"""
    return _shell("You've been invited to mradio web", content, _origin_of(link))
