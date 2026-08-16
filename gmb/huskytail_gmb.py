#!/usr/bin/env python3
"""HuskyTail Digital Google Business Profile posting publisher.

The publisher uses deterministic, logo-controlled media rather than AI image
rendering.  This prevents an image model from inventing another company's name
or logo in a customer-facing post.
"""

import argparse
import datetime
import hashlib
import io
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from gmb_post_lib import (
    check_dedup,
    get_access_token,
    get_google_oauth_credentials,
    load_state,
    post_to_gbp,
    preflight_gbp_local_posts,
    record_post,
    save_state,
    strip_phone_numbers,
    upload_to_github,
)

ACCOUNT_ID = "115031750744438008488"
LOCATION_ID = "4830251817171581358"
WEBSITE_URL = "https://www.huskytaildigital.com/?utm_source=gmb"
CTA_TYPE = "LEARN_MORE"
GITHUB_REPO = "stephen-huskytail/automation411"
GITHUB_SUBDIR = "gmb/huskytail"
STATE_FILE = os.path.join(os.path.dirname(__file__), "state_huskytail.json")
STATE_DEFAULTS = {"pillar_index": 0, "post_counts": {}, "last_post": None}
PILLARS = ["seo_education", "client_wins", "tool_trend", "lead_gen", "brand"]

BRAND_LOGO_PATH = Path(__file__).with_name("assets") / "huskytail-logo-white.webp"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BRAND_MEDIA_LABELS = {
    "seo_education": "LOCAL SEO, MADE CLEAR",
    "client_wins": "VISIBLE RESULTS",
    "tool_trend": "STAY AHEAD IN SEARCH",
    "lead_gen": "GET FOUND LOCALLY",
    "brand": "BUILT ON STRATEGY",
}

CONTENT = {
    "seo_education": {
        "texts": [
            "Your Google Business Profile is one of the most powerful free tools in local SEO — but most Las Vegas businesses aren't using it to its full potential.\n\nComplete your profile, post consistently, and respond to every review. These small steps compound into serious visibility over time.\n\nWant to see where your GBP stands? We offer free local visibility audits for businesses in Las Vegas, Henderson, and Summerlin.",
            "Did you know Google uses your Business Profile to decide who shows up in the local pack — those top 3 map results that capture the most clicks?\n\nKey factors: profile completeness, review velocity, consistent NAP data, and fresh posts. If you're not posting, a competitor who is will outrank you.\n\nHuskyTail Digital helps Las Vegas area businesses turn their GBP into a lead engine.",
            "Local SEO tip: your Google Business Profile categories matter more than most business owners realize.\n\nChoosing the right primary and secondary categories signals to Google exactly what you do and who you serve. Wrong categories = wrong audience.\n\nNot sure if your categories are optimized? We audit GBP profiles for free for businesses in Las Vegas, Henderson, and Summerlin NV.",
        ],
    },
    "client_wins": {
        "texts": [
            "A local service business in the Las Vegas valley came to us with zero online visibility — not showing up in local search, no reviews, and an incomplete Google Business Profile.\n\nWithin 90 days: first-page local results, 18 new reviews, and a 40% increase in website visits from search.\n\nSmall businesses deserve big results. See what's possible with the right local SEO strategy.",
            "A home services company in Henderson was getting edged out by competitors in Google Maps — despite being in business longer and having better reviews.\n\nThe problem? Their GBP was missing key service categories and hadn't been updated in months.\n\nWe corrected the profile, added consistent posts, and within 8 weeks they were back in the top 3. Consistent presence wins.",
            "A Summerlin-based professional services firm was invisible in local search despite serving the area for years.\n\nOur audit found 3 major GBP issues holding them back. Fixed, optimized, and posting consistently — they saw a 55% lift in profile views in the first month.\n\nIf you're not showing up locally, the fix is often simpler than you think.",
        ],
    },
    "tool_trend": {
        "texts": [
            "Google's AI Overviews are changing how local businesses get found.\n\nMore searches now show an AI summary at the top — and those summaries pull from your Google Business Profile, website, and reviews. If your GBP is incomplete or stale, you're invisible in the new AI-driven search.\n\nHuskyTail Digital helps Las Vegas businesses stay ahead of Google's evolving algorithm.",
            "Big GBP update: Google is placing more weight on recent activity when ranking local businesses.\n\nRegular posts, fresh photos, and prompt review responses all signal that your business is active and relevant. Businesses that haven't touched their profile in months are falling behind.\n\nNot sure if your profile is keeping up? Get a free audit from our team.",
            "The local search landscape is shifting. Google now factors in your website's E-E-A-T signals (Experience, Expertise, Authoritativeness, Trust) when ranking your Business Profile.\n\nFor Las Vegas businesses, that means your GBP and website need to work together — consistent messaging, matching categories, aligned content.\n\nWe help businesses build that alignment. Ask us about our local SEO strategy sessions.",
        ],
    },
    "lead_gen": {
        "texts": [
            "If your business isn't showing up in the top 3 Google Map results for your services, you're invisible to the majority of local searchers.\n\nMost people never scroll past those first results — which means your competitors are capturing leads that should be yours.\n\nWe offer free local visibility audits for Las Vegas, Henderson, and Summerlin businesses. Find out exactly where you stand and what it would take to move up.",
            "Quick question: when did you last Google your own business?\n\nIf you're not on page one of the local map pack, potential customers in Las Vegas are finding your competitors first.\n\nThe good news: local SEO is one of the highest-ROI investments a small business can make. And we'll show you exactly what's holding your ranking back — for free.",
            "Las Vegas has a lot of competition. Standing out in local search isn't optional anymore — it's the difference between a full calendar and an empty one.\n\nOur free GBP audit shows you: where you rank now, what your top competitors are doing differently, and the 3-5 changes that would move the needle fastest.\n\nBook your free audit. No obligation, no pitch.",
        ],
    },
    "brand": {
        "texts": [
            "HuskyTail Digital was built on a simple belief: Las Vegas small businesses deserve the same quality digital marketing that the big brands get.\n\nNo fluff. No vanity metrics. Just strategy that drives real visibility, real leads, and real growth.\n\nOh — and our mascot Everest the husky keeps us humble. 🐾",
            "We started HuskyTail Digital because we kept seeing great local businesses get buried in Google by competitors with worse services and better marketing.\n\nThat's not right. Good businesses deserve to be found.\n\nServing Las Vegas, Henderson, and Summerlin — built on strategy, backed by clarity.",
            "Behind every HuskyTail campaign is a real strategy, not a template.\n\nWe dig into your market, your competitors, and your actual goals before we touch a single setting. That's how we get results that stick.\n\nEverest our husky mascot approves of this approach. 🐾 Las Vegas local SEO done right.",
        ],
    },
}


def render_huskytail_brand_media(pillar: str) -> bytes:
    """Render a deterministic, HuskyTail-controlled 1536×1024 JPEG."""
    if pillar not in BRAND_MEDIA_LABELS:
        raise ValueError(f"Unknown HuskyTail media pillar: {pillar}")
    if not BRAND_LOGO_PATH.is_file():
        raise RuntimeError(f"Approved HuskyTail logo asset is missing: {BRAND_LOGO_PATH}")

    canvas = Image.new("RGB", (1536, 1024), "#071b35")
    draw = ImageDraw.Draw(canvas)
    for y in range(canvas.height):
        ratio = y / (canvas.height - 1)
        color = (7 + int(8 * ratio), 27 + int(32 * ratio), 53 + int(48 * ratio))
        draw.line((0, y, canvas.width, y), fill=color)
    draw.ellipse((850, -160, 1760, 750), fill="#1067c6")
    draw.ellipse((1050, 170, 1570, 690), fill="#1c8ff0")
    draw.rounded_rectangle((86, 84, 1450, 942), radius=44, outline="#2f9cf6", width=4)

    logo = Image.open(BRAND_LOGO_PATH).convert("RGBA")
    logo.thumbnail((600, 195), Image.Resampling.LANCZOS)
    canvas.paste(logo, (110, 130), logo)

    heading_font = ImageFont.truetype(FONT_PATH, 84)
    body_font = ImageFont.truetype(FONT_PATH, 34)
    draw.text((110, 420), BRAND_MEDIA_LABELS[pillar], font=heading_font, fill="white")
    draw.rectangle((110, 545, 410, 557), fill="#2f9cf6")
    draw.text((110, 610), "LAS VEGAS DIGITAL MARKETING", font=body_font, fill="#8bc7ff")
    draw.text((110, 666), "Built on Strategy. Backed by Clarity.", font=body_font, fill="white")
    draw.text((110, 775), "LOCAL SEO  •  CONTENT  •  GROWTH", font=body_font, fill="#8bc7ff")

    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=92, optimize=True)
    return out.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print selected post without API calls.")
    parser.add_argument("--preflight", action="store_true", help="Verify Google OAuth + GBP localPosts access without posting.")
    parser.add_argument("--render-brand-media", metavar="PATH", help="Render deterministic media locally without network access.")
    args = parser.parse_args()

    if args.render_brand_media:
        Path(args.render_brand_media).write_bytes(render_huskytail_brand_media("brand"))
        print(f"[HuskyTail GMB] Rendered reviewed HuskyTail brand media: {args.render_brand_media}")
        return

    state = load_state(STATE_FILE, STATE_DEFAULTS)
    if not (args.dry_run or args.preflight) and not check_dedup(state, guard_hours=20):
        return

    idx = state["pillar_index"] % len(PILLARS)
    pillar = PILLARS[idx]
    post_num = state["post_counts"].get(pillar, 0)
    text = strip_phone_numbers(CONTENT[pillar]["texts"][post_num % len(CONTENT[pillar]["texts"])])
    print(f"[HuskyTail GMB] Pillar: {pillar} (index {idx}), post #{post_num + 1}")
    print(f"[HuskyTail GMB] Text preview: {text[:80]}...")

    if args.dry_run:
        print("\n--- POST TEXT ---")
        print(text)
        print("\n--- BRAND MEDIA ---")
        print("Deterministic HuskyTail Digital logo-controlled artwork; no AI-generated logos or text.")
        return

    client_id, client_secret, refresh_token, google_oauth_label = get_google_oauth_credentials()
    print(f"[HuskyTail GMB] Refreshing Google access token via {google_oauth_label}...")
    token = get_access_token(client_id, client_secret, refresh_token)
    print("[HuskyTail GMB] Preflighting Google Business Profile localPosts endpoint...")
    preflight_gbp_local_posts(token, ACCOUNT_ID, LOCATION_ID)
    if args.preflight:
        print("[HuskyTail GMB] Preflight OK. No post created.")
        return

    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")
    if not github_token:
        raise RuntimeError("Missing GitHub token for HuskyTail GMB media upload")

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"gmb-{pillar}-{timestamp}.jpg"
    repo_path = f"{GITHUB_SUBDIR}/{filename}"
    print(f"[HuskyTail GMB] Rendering deterministic HuskyTail media for '{pillar}'...")
    jpeg_bytes = render_huskytail_brand_media(pillar)
    media_sha256 = hashlib.sha256(jpeg_bytes).hexdigest()[:12]
    print(f"[HuskyTail GMB] Brand media SHA-256: {media_sha256}")
    print(f"[HuskyTail GMB] Uploading image to GitHub: {repo_path}")
    cdn_url = upload_to_github(jpeg_bytes, GITHUB_REPO, repo_path, github_token, commit_message=f"HuskyTail GMB image: {filename}")
    print(f"[HuskyTail GMB] CDN URL: {cdn_url}")

    print("[HuskyTail GMB] Posting to Google Business Profile...")
    result = post_to_gbp(token, ACCOUNT_ID, LOCATION_ID, text, CTA_TYPE, WEBSITE_URL, cdn_url)
    print(f"[HuskyTail GMB] Post created: {result.get('name', 'unknown')}")

    state["pillar_index"] = (idx + 1) % len(PILLARS)
    state["post_counts"][pillar] = post_num + 1
    record_post(state)
    save_state(STATE_FILE, state)
    print(f"[HuskyTail GMB] Done. Next pillar: {PILLARS[state['pillar_index']]}. State saved.")


if __name__ == "__main__":
    main()
