"""Curated station list and genre logic, ported from the original mradio
(`DEFAULT_STATIONS`, `genre_of`, `genre_buckets`, `genre_stations_for`,
`genre_station_counts`). Stateless — no per-user data here."""

MAX_FAV = 12  # total favorites slots

GENRES = ("classical", "jazz", "blues", "country", "rock", "pop", "focus",
          "chill", "funk", "hiphop", "other")
GENRE_LABELS = {"classical": "Classical", "jazz": "Jazz",
                "blues": "Blues", "country": "Country", "rock": "Rock",
                "pop": "Pop", "focus": "Focus", "chill": "Chill",
                "funk": "Funk", "hiphop": "Hip-Hop", "other": "Other"}

_GENRE_KEYWORDS = {
    "blues": ("blues",),
    "jazz": ("jazz", "swing", "bigband", "big band"),
    "classical": ("classic", "classical", "orchestra", "orchestral", "chamber",
                  "opera", "baroque", "symphony", "klassik", "klassiek",
                  "musique", "recital", "sonata", "concerto"),
    "country": ("country", "americana", "bluegrass", "honky tonk", "honky-tonk",
                "nash"),
    "rock": ("rock", "rockabilly", "metal", "hard rock", "punk"),
    "pop": ("pop", "top 40", "top40", "hits"),
    "focus": ("focus", "meditation", "meditat", "relax", "new age", "newage",
              "yoga", "zen", "ambient", "drone", "instrumental"),
    "chill": ("chill", "chillout", "lounge", "downtempo", "del mar"),
    "funk": ("funk", "funky", "groove", "grooves", "boogie", "soul", "r&b",
             "rnb", "rhythm and blues", "disco funk", "jazz funk"),
    "hiphop": ("hip hop", "hip-hop", "hiphop", "rap", "urban", "jamz"),
}

DEFAULT_STATIONS = [
    # First 12 = the seeded favorites for brand-new accounts (see
    # userdata.py's _load_favorites_sync "first run for this user"
    # branch, which reads DEFAULT_STATIONS[:MAX_FAV]). Set once,
    # 2026-09-06, per the user's explicit one-time favorites reset —
    # see MEMORY.md. Not meant to be reordered casually going forward;
    # existing users' own favorites are never re-synced from this list.
    {"name": "VCR Auditorium | Venice Classic Radio Italia",
     "url": "https://uk2.streamingpulse.com/ssl/vcr1", "genre": "classical"},
    {"name": "VCR Classica+ | Venice Classic Radio Italia",
     "url": "https://uk2.streamingpulse.com/ssl/vcr2", "genre": "classical"},
    {"name": "Radio Swiss Classic",
     "url": "https://stream.srg-ssr.ch/srgssr/rsc_it/mp3/128", "genre": "classical"},
    {"name": "181.FM Kickin' Country",
     "url": "http://listen.181fm.com/181-kickincountry_128k.mp3", "genre": "country"},
    {"name": "1.FM Absolute Country Hits",
     "url": "http://strm112.1.fm/acountry_mobile_mp3", "genre": "country"},
    {"name": "Swiss Jazz", "url": "http://stream.srg-ssr.ch/m/rsj/mp3_128",
     "genre": "jazz"},
    {"name": "Radio Paradise",
     "url": "https://stream.radioparadise.com/mp3-320", "genre": "other"},
    {"name": "Jazz Radio Blues",
     "url": "http://jazzblues.ice.infomaniak.ch/jazzblues-high.mp3",
     "genre": "blues"},
    {"name": "Heart 70s (UK)", "url": "https://media-ssl.musicradio.com/Heart70sMP3",
     "genre": "pop"},
    {"name": "181.FM True Blues",
     "url": "http://listen.181fm.com/181-blues_128k.mp3", "genre": "blues"},
    {"name": "Jazz Lounge", "url": "http://eu8.fastcast4u.com:5068/", "genre": "chill"},
    {"name": "Funkstar Radio",
     "url": "https://funkstar.radioca.st/stream", "genre": "funk"},
    # ---- everything below is the rest of the curated catalogue, still
    # browsable under Genres, no longer part of the default favorites ----
    {"name": "Naim Classical",
     "url": "http://mscp3.live-streams.nl:8250/class-high.aac", "genre": "classical"},
    {"name": "WQXR", "url": "https://stream.wqxr.org/wqxr.mp3", "genre": "classical"},
    {"name": "Classic FM", "url": "http://ice-the.musicradio.com/ClassicFMMP3",
     "genre": "classical"},
    {"name": "radio klassik Stephansdom",
     "url": "http://radioklassikstephansdom.ice.infomaniak.ch/"
            "radioklassikstephansdom.mp3", "genre": "classical"},
    {"name": "NPO Klassiek",
     "url": "https://icecast.omroep.nl/radio4-bb-mp3", "genre": "classical"},
    {"name": "France Musique",
     "url": "https://icecast.radiofrance.fr/francemusique-midfi.mp3",
     "genre": "classical"},
    {"name": "WCRB",
     "url": "https://wgbh-live.streamguys1.com/classical-hi", "genre": "classical"},
    {"name": "KUSC",
     "url": "https://playerservices.streamtheworld.com/api/livestream-redirect/KUSCMP256.mp3",
     "genre": "classical"},
    {"name": "WFMT",
     "url": "https://wfmt.streamguys1.com/main-source", "genre": "classical"},
    {"name": "BBC Radio 3",
     "url": "http://a.files.bbci.co.uk/ms6/live/3441A116-B12E-4D2F-ACA8-"
            "C1984642FA4B/audio/simulcast/hls/nonuk/audio_syndication_low_sbr_"
            "v1/ak/bbc_radio_three.m3u8", "genre": "other"},
    {"name": "WBGO", "url": "https://ais-sa8.cdnstream1.com/3629_128.mp3",
     "genre": "jazz"},
    {"name": "WWOZ", "url": "http://wwoz-sc.streamguys.com/wwoz-hi.mp3",
     "genre": "jazz"},
    {"name": "KCSM 91.1",
     "url": "http://ice7.securenetsystems.net/KCSM2", "genre": "jazz"},
    {"name": "KJAZZ 88.1",
     "url": "https://streaming.live365.com/a49833", "genre": "jazz"},
    {"name": "Jazz24",
     "url": "https://knkx-live-a.edge.audiocdn.com/6285_256k", "genre": "jazz"},
    {"name": "1.FM Adore Jazz",
     "url": "http://strm112.1.fm/ajazz_mobile_mp3", "genre": "jazz"},
    {"name": "TSF Jazz",
     "url": "http://tsfjazz.ice.infomaniak.ch/tsfjazz-high.mp3", "genre": "jazz"},
    {"name": "JazzRadio 106.8 Berlin",
     "url": "https://streaming.radio.co/s774887f7b/listen", "genre": "jazz"},
    {"name": "KMHD",
     "url": "https://ais-sa3.cdnstream1.com/2442_128.aac", "genre": "jazz"},
    {"name": "Blues Radio Greece",
     "url": "http://cast3.radiohost.ovh:8352/", "genre": "blues"},
    {"name": "Blues Music Fan",
     "url": "https://orbit.citrus3.com:8052/stream", "genre": "blues"},
    {"name": "Blues Rock Cafe",
     "url": "https://bluesrockcafe.stream.laut.fm/bluesrockcafe",
     "genre": "blues"},
    {"name": "1.FM Blues",
     "url": "http://strm112.1.fm/blues_mobile_mp3", "genre": "blues"},
    {"name": "Buddy Guy Radio Legends",
     "url": "https://streaming.live365.com/a83090", "genre": "blues"},
    {"name": "WDCB 90.9",
     "url": "https://wdcb-ice.streamguys1.com/wdcb128", "genre": "blues"},
    {"name": "exclusive BB King",
     "url": "https://streaming.exclusive.radio/er/bbking/icecast.audio",
     "genre": "blues"},
    {"name": "Radio Caprice - Chicago Blues",
     "url": "http://79.111.14.76:8000/chicagoblues", "genre": "blues"},
    {"name": "WSM 650 AM (Nashville)", "url": "http://stream01048.westreamradio.com/wsm-am-mp3",
     "genre": "country"},
    {"name": ".977 Country", "url": "http://26343.live.streamtheworld.com/977_COUNTRY_SC",
     "genre": "country"},
    {"name": "1.FM Classic Country",
     "url": "http://strm112.1.fm/ccountry_mobile_mp3", "genre": "country"},
    {"name": "181.FM Highway 181",
     "url": "http://listen.181fm.com/181-highway_128k.mp3", "genre": "country"},
    {"name": "181.FM Real Country",
     "url": "http://listen.181fm.com/181-realcountry_128k.mp3", "genre": "country"},
    {"name": "KIX Country (AU)", "url": "http://playerservices.streamtheworld.com/api/livestream-redirect/KIXCOUNTRY.mp3",
     "genre": "country"},
    {"name": "Big R Radio Country",
     "url": "http://bigrradio.cdnstream1.com/5195_128", "genre": "country"},
    {"name": "America's Country", "url": "https://ais-sa2.cdnstream1.com/1976_128.mp3",
     "genre": "country"},
    {"name": "Radio Caroline", "url": "http://78.129.202.200:8040/", "genre": "rock"},
    {"name": "Virgin Classic Rock (IT)",
     "url": "http://icy.unitedradio.it/VirginRockClassics.mp3", "genre": "rock"},
    {"name": "Rock Antenne", "url": "http://mp3channels.webradio.rockantenne.de/rockantenne",
     "genre": "rock"},
    {"name": "Arrow Classic Rock", "url": "http://stream.gal.io/arrow", "genre": "rock"},
    {"name": "1.FM Classic Rock Replay",
     "url": "http://strm112.1.fm/crock_mobile_mp3", "genre": "rock"},
    {"name": "SomaFM Left Coast 70s (Rock)",
     "url": "https://ice2.somafm.com/seventies-320-mp3", "genre": "rock"},
    {"name": "Radio ROKS Hard'n'Heavy",
     "url": "http://online.radioroks.ua/RadioROKS_HardnHeavy_HD", "genre": "rock"},
    {"name": "Radio ROKS Ballads",
     "url": "http://online.radioroks.ua/RadioROKS_Ballads_HD", "genre": "rock"},
    {"name": "181.FM Rock 181", "url": "http://listen.181fm.com/181-rock_128k.mp3",
     "genre": "rock"},
    {"name": "Hard Rock Heaven", "url": "http://hydra.cdnstream.com/1521_128",
     "genre": "rock"},
    {"name": "Capital FM London (UK)",
     "url": "https://media-ssl.musicradio.com/CapitalMP3", "genre": "pop"},
    {"name": "Heart 80s (UK)", "url": "https://media-ssl.musicradio.com/Heart80sMP3",
     "genre": "pop"},
    {"name": "Radio 105 Italy", "url": "http://icecast.unitedradio.it/Radio105.mp3",
     "genre": "pop"},
    {"name": "LOS 40 España",
     "url": "https://playerservices.streamtheworld.com/api/livestream-redirect/Los40.mp3",
     "genre": "pop"},
    {"name": "Radio 538 (NL)",
     "url": "http://playerservices.streamtheworld.com/api/livestream-redirect/RADIO538.mp3",
     "genre": "pop"},
    {"name": "Energy Zürich (NRJ, CH)",
     "url": "http://broadcast.infomaniak.ch/energyzuerich-high.mp3", "genre": "pop"},
    {"name": "1.FM Absolute TOP 40",
     "url": "http://strm112.1.fm/top40_mobile_mp3", "genre": "pop"},
    {"name": "SWR3 (DE)", "url": "https://liveradio.swr.de/sw282p3/swr3/play.mp3",
     "genre": "pop"},
    {"name": "Chocolate FM (ES)", "url": "http://streaming5.elitecomunicacion.es:8082/live.mp3",
     "genre": "pop"},
    {"name": "SomaFM Space Station Soma",
     "url": "https://ice5.somafm.com/spacestation-320-mp3", "genre": "focus"},
    {"name": "Ambient Sleeping Pill", "url": "http://radio.stereoscenic.com/asp-h",
     "genre": "focus"},
    {"name": "SomaFM Drone Zone",
     "url": "https://ice2.somafm.com/dronezone-128-mp3", "genre": "focus"},
    {"name": "SomaFM Groove Salad",
     "url": "https://ice5.somafm.com/groovesalad-128-mp3", "genre": "focus"},
    {"name": "Cryosleep (Echoes of Blue Mars)",
     "url": "http://streams.echoesofbluemars.org:8000/cryosleep", "genre": "focus"},
    {"name": "SomaFM Deep Space One",
     "url": "https://ice2.somafm.com/deepspaceone-128-mp3", "genre": "focus"},
    {"name": "Radio Caprice - Relaxation Music",
     "url": "http://79.120.39.202:9109/", "genre": "focus"},
    {"name": "Total Instrumental (laut.fm)",
     "url": "http://stream.laut.fm/total-instrumental", "genre": "focus"},
    {"name": "Yoga Chill", "url": "http://178.32.111.41:8027/stream-128kmp3-YogaChill",
     "genre": "focus"},
    {"name": "Radio Art - Deep Focus & Concentration",
     "url": "https://air.radioart.online/fDeep_focus.mp3", "genre": "focus"},
    {"name": "1.FM Chillout Lounge",
     "url": "http://strm112.1.fm/chilloutlounge_mobile_mp3", "genre": "chill"},
    {"name": "Chilltrax", "url": "http://server1.chilltrax.com:9000/", "genre": "chill"},
    {"name": "Café del Mar", "url": "https://streams.radio.co/se1a320b47/listen",
     "genre": "chill"},
    {"name": "Smooth Chill (UK)",
     "url": "https://media-ssl.musicradio.com/ChillMP3", "genre": "chill"},
    {"name": "Antenne Bayern Chillout",
     "url": "http://mp3channels.webradio.antenne.de/chillout", "genre": "chill"},
    {"name": "SomaFM Fluid", "url": "https://ice6.somafm.com/fluid-128-mp3",
     "genre": "chill"},
    {"name": "Costa del Mar - Chillout",
     "url": "http://stream.cdm-chillout.com:8020/stream-AAC-Chill", "genre": "chill"},
    {"name": "Hi On Line Lounge",
     "url": "http://mediaserv33.live-streams.nl:8036/live", "genre": "chill"},
    {"name": "Costa del Mar - Zen",
     "url": "http://stream.cdm-zen.com:8004/stream-mp3-Zen", "genre": "chill"},
    {"name": "Amsterdam Funk Channel",
     "url": "https://live.afc.fm", "genre": "funk"},
    {"name": "Funky Radio Classic Funk",
     "url": "http://funkyradio.streamingmedia.it:8001/play.mp3", "genre": "funk"},
    {"name": "Radio Meuh",
     "url": "http://radiomeuh.ice.infomaniak.ch/radiomeuh-128.mp3", "genre": "funk"},
    {"name": "Capital Jazz Radio",
     "url": "http://stream.radio.co/s7c1ea5960/listen", "genre": "funk"},
    {"name": "Funk the Planet",
     "url": "https://streaming.live365.com/a01484", "genre": "funk"},
    {"name": "DanceGroove Radio",
     "url": "http://s13.streamingcloud.online:34128", "genre": "funk"},
    {"name": "Funk42 Radio",
     "url": "http://213.133.97.249:8843/stream", "genre": "funk"},
    {"name": "Ministry of Soul",
     "url": "https://soul.stream.laut.fm/soul", "genre": "funk"},
    {"name": "Funky Radio Disco Funk",
     "url": "https://funky.radio/discofunk_modernsoul_boogie/", "genre": "funk"},
    {"name": "181.FM - Old School HipHop/RnB",
     "url": "http://listen.181fm.com/181-oldschool_128k.mp3", "genre": "hiphop"},
    {"name": "181.FM - The Beat (HipHop/R&B)",
     "url": "https://listen.181fm.com/181-beat_128k.mp3", "genre": "hiphop"},
    {"name": "90s90s HipHop & Rap",
     "url": "http://streams.90s90s.de/hiphop/mp3-192/streams.90s90s.de/",
     "genre": "hiphop"},
    {"name": "100 Hip Hop and RNB FM",
     "url": "https://ice64.securenetsystems.net/LFTM", "genre": "hiphop"},
    {"name": ".977 Jamz",
     "url": "http://26343.live.streamtheworld.com:3690/977_JAMZ_SC",
     "genre": "hiphop"},
    {"name": "BBC Radio 1Xtra",
     "url": "https://a.files.bbci.co.uk/ms6/live/3441A116-B12E-4D2F-ACA8-"
            "C1984642FA4B/audio/simulcast/hls/nonuk/audio_syndication_low_sbr_"
            "v1/aks/bbc_1xtra.m3u8", "genre": "hiphop"},
    {"name": "All Underground Hip Hop Radio",
     "url": "http://stream.radiojar.com/c1912tk5rtzuv", "genre": "hiphop"},
    {"name": "WEFUNK",
     "url": "https://s-17.wefunkradio.com:8443/wefunk64.mp3", "genre": "hiphop"},
    {"name": "Hot 108 Jamz",
     "url": "https://live.powerhitz.com/hot108", "genre": "hiphop"},
    {"name": "Top Urbano",
     "url": "https://radio.dominiserver.com/proxy/topurbano?mp=/stream",
     "genre": "hiphop"},
]


def genre_of(name):
    """Best-effort genre for a station by its name; 'other' when unknown."""
    n = (name or "").lower()
    for genre in ("blues", "jazz", "country", "rock", "pop", "focus", "chill",
                  "funk", "hiphop", "classical"):
        for kw in _GENRE_KEYWORDS[genre]:
            if kw in n:
                return genre
    return "other"


def is_empty_slot(e):
    """True if `e` is a placeholder for an empty (deleted) favorites slot."""
    return e is None


def genre_buckets(stations):
    """Split a station list into {genre: [stations...]} preserving input order.
    Only genres that have at least one station are included."""
    out = {g: [] for g in GENRES}
    for ent in stations or []:
        g = str((ent or {}).get("genre") or "").strip()
        if g not in out:
            g = "other"
        out[g].append(ent)
    return out


def genre_stations_for(fav_stations, genre):
    """Stations shown in a genre view: the user's favorites in that genre,
    plus the curated stations from DEFAULT_STATIONS (de-duplicated). The
    favorites file is never touched. 'other' stays favorites-only."""
    favs = [e for e in (fav_stations or [])
            if not is_empty_slot(e)
            and (e.get("genre") or "other") == genre]
    if genre not in ("classical", "jazz", "blues", "country", "rock", "pop",
                     "focus", "chill", "funk", "hiphop"):
        return favs
    seen = set()
    out = []
    for ent in favs + [s for s in DEFAULT_STATIONS
                       if (s.get("genre") or "") == genre]:
        key = ((ent.get("name") or "").strip(), (ent.get("url") or "").strip())
        if key in seen:
            continue
        seen.add(key)
        out.append(ent)
    return out


def genre_station_counts(fav_stations):
    """Per-genre counts: favorites, plus curated genres."""
    return {g: len(genre_stations_for(fav_stations, g)) for g in GENRES}
