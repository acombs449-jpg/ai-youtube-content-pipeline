"""One-time: file existing uploads into the right playlists."""
import json
import config
from pipeline import youtube_upload

ASSIGN = {
    "8sY11JAU0Tw": "Budgeting Basics",        # 50/30/20 rule
    "SJXuknA3ZJE": "Budgeting Basics",        # pay stub decoded
    "NjTaEkSqSAY": "Budgeting Basics",        # can you afford it number
    "LScoe8-P_h4": "Saving Money",            # emergency fund
    "9xonLyU-70E": "Saving Money",            # deductible
    "YiKrM0766j4": "Saving Money",            # bank vs credit union
    "0WE2dUNjgcE": "Saving Money",            # routing vs account number
    "g-Fs_u8KnYA": "Crush Your Debt",         # minimum payments
    "EB42uFQ1E2Y": "Build Your Credit",       # grace period
    "eNWfeaupRO8": "Build Your Credit",       # credit score
    "K0O3QYCBwX0": "Money Habits & Mindset",  # beneficiary
}


def main():
    ids = json.loads((config.ROOT / "playlists.json").read_text(encoding="utf-8"))
    yt = youtube_upload._service()
    for vid, plname in ASSIGN.items():
        try:
            yt.playlistItems().insert(
                part="snippet",
                body={"snippet": {
                    "playlistId": ids[plname],
                    "resourceId": {"kind": "youtube#video", "videoId": vid},
                }},
            ).execute()
            print(f"{vid} -> {plname}")
        except Exception as e:
            print(f"{vid} FAILED: {e}")


if __name__ == "__main__":
    main()
