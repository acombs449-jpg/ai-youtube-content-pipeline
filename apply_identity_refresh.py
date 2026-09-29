"""Apply a channel identity refresh: regenerate the banner with new
headline/tagline, then push banner + About description + keywords live via
the YouTube API. Takes the winning package from the identity-refresh design
panel as a JSON file (or edit the FALLBACK dict below and run with no args).

Usage:
    python apply_identity_refresh.py path/to/winning_design.json
    python apply_identity_refresh.py            # uses FALLBACK below
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config
from pipeline import youtube_upload
from branding.make_brand import banner as render_banner

FALLBACK = None  # set to a dict matching the design schema to use without a file


def _keywords_string(keywords: list[str]) -> str:
    # YouTube's brandingSettings.channel.keywords is one space-separated string;
    # multi-word phrases must be quoted so they aren't split into separate tags.
    parts = [f'"{k}"' if " " in k else k for k in keywords]
    return " ".join(parts)[:500]  # API enforces a ~500 char limit


def main():
    if len(sys.argv) > 1:
        design = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    elif FALLBACK:
        design = FALLBACK
    else:
        raise SystemExit("Pass a design JSON file, or set FALLBACK in this script.")

    print("Regenerating banner...")
    render_banner(headline=design["banner_headline"], tagline=design["banner_tagline"])
    banner_path = config.ROOT / "branding" / "yt_banner.png"

    yt = youtube_upload._service()

    print("Uploading banner image...")
    from googleapiclient.http import MediaFileUpload
    up = yt.channelBanners().insert(
        media_body=MediaFileUpload(str(banner_path), mimetype="image/png")
    ).execute()
    banner_url = up["url"]

    print("Updating channel branding (banner + about + keywords)...")
    ch = yt.channels().list(part="brandingSettings", mine=True).execute()
    item = ch["items"][0]
    cid = item["id"]
    bs = item.get("brandingSettings", {})
    bs.setdefault("channel", {})
    bs["channel"]["description"] = design["about_description"]
    bs["channel"]["keywords"] = _keywords_string(design["keywords"])
    bs.setdefault("image", {})["bannerExternalUrl"] = banner_url
    yt.channels().update(part="brandingSettings", body={"id": cid, "brandingSettings": bs}).execute()

    print("\nDone. Channel identity updated:")
    print(f"  About: {design['about_description'][:120]}...")
    print(f"  Banner: {design['banner_headline']} / {design['banner_tagline']}")
    print(f"  Keywords: {len(design['keywords'])} terms")


if __name__ == "__main__":
    main()
