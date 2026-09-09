"""HTML bodies for outbound transactional email — password reset and the
new-account welcome/invite. Table-based, inline-styled markup only (no
external stylesheet, no flexbox/grid, no CSS custom properties): this is
rendered by real email clients, not a browser, and Outlook's Word-based
engine and Gmail's stylesheet stripping rule out anything else. Colors
are the app's own dark-theme tokens (frontend/src/index.css), converted
from OKLCH to hex by hand since email clients don't parse oklch().

Hallmark · macrostructure: single-column centered card (email genre) ·
theme: mradio-web dark (paper #111419, ink #edebe7, teal accent #35b9c0,
Newsreader-style serif headline / system sans body) · logo: flat
single-path recreation of the favicon's arrow mark (blur/glow filters
and gradient dropped — neither renders reliably in email clients)."""

_PAPER = "#111419"
_PAPER_2 = "#191d24"
_INK = "#edebe7"
_INK_2 = "#c0bdb8"
_INK_3 = "#89867f"
_LINE = "#333841"
_ACCENT = "#35b9c0"
_ACCENT_INK = "#e0f3f4"

_FONT_DISPLAY = "Georgia, 'Times New Roman', serif"
_FONT_BODY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

# Flat single-path recreation of favicon.svg's outer silhouette — the
# original's blur filters, mask, and gradient decoration are dropped
# entirely (neither renders reliably across email clients), leaving
# just the bolt/arrow shape as one solid teal fill. Shipped as a real
# PNG (frontend/public/email-logo.png, built into frontend/dist and
# served by the app's own static mount) referenced by absolute URL —
# NOT inline <svg>: Outlook desktop's Word-based rendering engine
# doesn't render inline SVG at all, only Gmail/Apple Mail/modern
# webmail do, confirmed via research before choosing this over the
# simpler inline-SVG approach the first draft used.
def _logo_img(base_url: str) -> str:
    src = f"{base_url}/email-logo.png" if base_url else "email-logo.png"
    return (f'<img src="{src}" width="56" height="54" alt="mradio web" '
            'style="display:block; border:0; outline:none;">')


def _shell(preheader: str, content_html: str, base_url: str) -> str:
    """Wraps a card of content in the outer document — dark page
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


def password_reset_html(link: str) -> str:
    """Calm and factual on purpose — no charm, no exclamation marks: a
    forgot-password moment is a frustration path (copy.md explicitly
    bans humor there), not an occasion for personality."""
    content = f"""
<h1 style="margin:0 0 16px; font-family:{_FONT_DISPLAY}; font-size:24px; font-weight:400; color:{_INK}; line-height:1.3;">
Reset your password
</h1>
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


def welcome_html(full_name_or_username: str, link: str) -> str:
    """The one email in this app that's allowed real warmth — an
    invitation, not a transaction. "Someone wonderful has invited
    you..." is the Plex-style heading the user specifically asked for."""
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
<p style="margin:0; font-family:{_FONT_BODY}; font-size:15px; line-height:1.6; color:{_INK_2};">
You&rsquo;ve got an account on mradio web &mdash; a self-hosted radio player with live now-playing details and AI-written liner notes for whatever&rsquo;s on. Set your password and you&rsquo;re in.
</p>
{_button('Set your password', link)}
<p style="margin:0 0 24px; font-family:{_FONT_BODY}; font-size:13px; line-height:1.6; color:{_INK_3};">
This link expires in 7 days and can only be used once.
</p>
<hr style="border:none; border-top:1px solid {_LINE}; margin:0 0 24px;">
{_fallback_link(link)}
"""
    return _shell("You've been invited to mradio web", content, _origin_of(link))
