# Music service playlist integration — investigation findings

Date: 2026-09-12
Scope: find services that let a user export/"star" a track from mradio-web into their own playlist, comparable to the existing Spotify integration.

## Executive summary

- **Spotify** works technically but is blocked because the Spotify Developer app owner needs an active Premium subscription.
- **Apple Music** is technically possible but has a hard gate: a paid Apple Developer Program membership (~$99/year) is required to generate the developer token used by MusicKit / the Apple Music Web API. End users also need an Apple Music subscription.
- **Deezer** is the best drop-in replacement: public OAuth API, free developers, free users can create/modify playlists, and the flow mirrors Spotify.
- **Amazon Music** and **Tidal** have no public write API for third-party playlist creation.
- **YouTube Music** has no official public API; only reverse-engineered/unofficial clients that carry ToS risk.
- **SoundCloud** has a public OAuth API for playlist creation, but its catalog skews toward user-uploaded content and is less useful for mainstream radio tracks.

## Apple Music

Apple provides two pieces:

1. **MusicKit JS** — gets a Music User Token from the browser after the user authorizes.
2. **Apple Music Web API (REST)** — the actual endpoints for creating/modifying library playlists.

Relevant endpoints:

- `POST https://api.music.apple.com/v1/me/library/playlists` — create a library playlist
- `POST https://api.music.apple.com/v1/me/library/playlists/{id}/tracks` — add tracks

Auth headers:

- `Authorization: Bearer <developer_token>`
- `Music-User-Token: <music_user_token>`

The developer token is a JWT signed with a private key downloaded from the Apple Developer portal. Generating the key and configuring a MusicKit identifier requires an Apple Developer Program membership.

Sources:

- [Create a Library Playlist — Apple Developer](https://developer.apple.com/documentation/applemusicapi/create_a_library_playlist)
- [Add Tracks to a Library Playlist — Apple Developer](https://developer.apple.com/documentation/applemusicapi/add_tracks_to_a_library_playlist)
- [MusicKit JS docs](https://js.music.apple.com/musickit/v3/docs/index.html)

### Do you have to pay the $100/year fee?

Yes. The Apple Developer Program costs **$99/year** for individuals/organizations. Apple Developer Enterprise is $299/year. A paid membership is required to create the private key and MusicKit identifier needed for the developer token. Some forum posts claim limited testing is possible with a free Apple ID, but the official path to a production token is the paid program.

Sources:

- [Apple Developer Program — Membership](https://developer.apple.com/programs/)
- [Generate Developer Tokens for Apple Music API — Apple Developer](https://developer.apple.com/documentation/applemusicapi/generating_developer_tokens)

## SoundHound and Shazam — what they do besides Spotify

Both apps started as song-identification tools but now act as music-discovery hubs with streaming integrations.

### SoundHound

- Integrates with **Spotify and Apple Music** for full-track playback and playlist additions.
- Core features beyond identification:
  - Real-time lyrics ("LiveLyrics")
  - Voice control ("Hey SoundHound")
  - Charts and discovery feeds
  - Artist pages, albums, videos
  - Hands-free music search

Source:

- [SoundHound app page](https://music.soundhound.com/soundhound)

### Shazam

- Owned by Apple since 2018.
- Connects to **Apple Music, Spotify, Deezer, and YouTube Music** depending on region/platform.
- Core features beyond identification:
  - Auto-adds identified tracks to an Apple Music "My Shazam Tracks" playlist
  - Charts, radio spins, artist bios
  - Concert/tour dates
  - Music videos and lyric sync
  - Weekly "New and Rising" / "Going Viral" insights

Sources:

- [Shazam homepage](https://www.shazam.com/)
- [Shazam — Apple](https://www.apple.com/shazam/)

## Service comparison matrix

| Service | Public write API | Auth model | Developer cost | End-user cost | Notes |
|---|---|---|---|---|---|
| **Spotify** | Yes | OAuth 2.0 | Free | Free (but app owner must have Premium) | Currently blocked by Premium-owner rule |
| **Apple Music** | Yes | MusicKit JS + JWT dev token | $99/year Apple Developer | Apple Music subscription | Robust but gated by fee + subscription |
| **Deezer** | Yes | OAuth 2.0 | Free | Free accounts can create playlists | Best drop-in replacement |
| **SoundCloud** | Yes | OAuth 2.0 | Free | Free accounts can create playlists | Catalog is user-uploaded, less radio-friendly |
| **YouTube Music** | No official | N/A | N/A | N/A | Unofficial `ytmusicapi` exists but violates ToS |
| **Amazon Music** | No public | N/A | N/A | N/A | Only partner/Alexa APIs, not playlist write |
| **Tidal** | No public | N/A | N/A | N/A | Partner-only; no self-service playlist API |

## Deezer API details

Deezer uses OAuth 2.0. The relevant permission scope is `manage_library`.

Endpoints:

- Create playlist: `POST https://api.deezer.com/user/me/playlists` with `title` and `access_token`
- Add tracks: `POST https://api.deezer.com/playlist/{id}/tracks` with `songs={comma-separated-track-ids}` and `access_token`

Scopes of interest:

- `basic_access` — read basic user info
- `email` — access email
- `offline_access` — refresh token
- `manage_library` — create playlists, add/remove tracks, manage favorites

Authorization URL pattern:

```
https://connect.deezer.com/oauth/auth.php?app_id=APP_ID&redirect_uri=URI&perms=manage_library
```

Token exchange endpoint:

```
https://connect.deezer.com/oauth/access_token.php?app_id=APP_ID&secret=SECRET&code=CODE
```

Sources:

- [Deezer Developers](https://developers.deezer.com/)
- [Deezer API — user playlists endpoint](https://developers.deezer.com/api/user/playlists)
- [Deezer API — playlist tracks endpoint](https://developers.deezer.com/api/playlist/tracks)

## Recommendations

1. **Park Spotify** until a Premium account owns the Spotify Developer app.
2. **Add Deezer next.** It has the closest shape to the existing Spotify integration (OAuth, free dev account, free user accounts, playlist create/add endpoints) and is the fastest path to a working "star to playlist" feature.
3. **Defer Apple Music** unless you are already paying for the Apple Developer Program and your users are mostly Apple Music subscribers. The $99/year fee and the MusicKit token complexity make it a second-tier priority.
4. **Skip Amazon Music, Tidal, and YouTube Music** for now — none offer a public, ToS-safe way to write playlists.
5. **Keep SoundCloud as a stretch option** if users request it, but be aware that its catalog is mostly user-uploaded content, so matching radio tracks will be less reliable.
