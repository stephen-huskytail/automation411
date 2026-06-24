#!/usr/bin/env python3
"""
HuskyTail Digital GMB Posting Script
Schedule: every 3 days at 9am PT (0 16 */3 * * UTC)
Pillar rotation: seo_education → client_wins → tool_trend → lead_gen → brand
"""

import os
import sys
import datetime

# Add parent dir to path for shared lib
sys.path.insert(0, os.path.dirname(__file__))
from gmb_post_lib import (
    get_access_token, post_to_gbp, strip_phone_numbers,
    check_dedup, record_post, load_state, save_state,
    generate_image, upload_to_github,
)

# ── Config ────────────────────────────────────────────────────────────────────

ACCOUNT_ID  = "115031750744438008488"
LOCATION_ID = "4830251817171581358"
WEBSITE_URL = "https://www.huskytaildigital.com/?utm_source=gmb"
CTA_TYPE    = "LEARN_MORE"

GITHUB_REPO   = "stephen-huskytail/automation411"
GITHUB_SUBDIR = "gmb/huskytail"

STATE_FILE = os.path.join(os.path.dirname(__file__), "state_huskytail.json")

STATE_DEFAULTS = {
    "pillar_index": 0,
    "post_counts": {},
    "last_post": None,
}

PILLARS = [
    "seo_education",
    "client_wins",
    "tool_trend",
    "lead_gen",
    "brand",
]

# ── Content templates ─────────────────────────────────────────────────────────

CONTENT = {
    "seo_education": {
        "texts": [
            "Your Google Business Profile is one of the most powerful free tools in local SEO — but most Las Vegas businesses aren't using it to its full potential.\n\nComplete your profile, post consistently, and respond to every review. These small steps compound into serious visibility over time.\n\nWant to see where your GBP stands? We offer free local visibility audits for businesses in Las Vegas, Henderson, and Summerlin.",
            "Did you know Google uses your Business Profile to decide who shows up in the local pack — those top 3 map results that capture the most clicks?\n\nKey factors: profile completeness, review velocity, consistent NAP data, and fresh posts. If you're not posting, a competitor who is will outrank you.\n\nHuskyTail Digital helps Las Vegas area businesses turn their GBP into a lead engine.",
            "Local SEO tip: your Google Business Profile categories matter more than most business owners realize.\n\nChoosing the right primary and secondary categories signals to Google exactly what you do and who you serve. Wrong categories = wrong audience.\n\nNot sure if your categories are optimized? We audit GBP profiles for free for businesses in Las Vegas, Henderson, and Summerlin NV.",
        ],
        "image_prompts": [
            "Professional digital marketing infographic showing Google Business Profile optimization checklist, clean flat design, blue and white color scheme, Las Vegas cityscape in background, 16:9 aspect ratio",
            "Modern SEO dashboard illustration showing local map pack rankings, star ratings, and review metrics, professional marketing agency aesthetic, 16:9 aspect ratio",
            "Clean business infographic showing local search ranking factors with icons for reviews, photos, posts, and categories, professional navy blue and white design, 16:9",
        ],
    },
    "client_wins": {
        "texts": [
            "A local service business in the Las Vegas valley came to us with zero online visibility — not showing up in local search, no reviews, and an incomplete Google Business Profile.\n\nWithin 90 days: first-page local results, 18 new reviews, and a 40% increase in website visits from search.\n\nSmall businesses deserve big results. See what's possible with the right local SEO strategy.",
            "A home services company in Henderson was getting edged out by competitors in Google Maps — despite being in business longer and having better reviews.\n\nThe problem? Their GBP was missing key service categories and hadn't been updated in months.\n\nWe corrected the profile, added consistent posts, and within 8 weeks they were back in the top 3. Consistent presence wins.",
            "A Summerlin-based professional services firm was invisible in local search despite serving the area for years.\n\nOur audit found 3 major GBP issues holding them back. Fixed, optimized, and posting consistently — they saw a 55% lift in profile views in the first month.\n\nIf you're not showing up locally, the fix is often simpler than you think.",
        ],
        "image_prompts": [
            "Professional before-and-after SEO results graphic showing upward trending analytics chart, green growth arrows, clean modern design, Las Vegas business district backdrop, 16:9 aspect ratio",
            "Split screen comparison graphic showing low vs high local search visibility for a small business, professional marketing infographic style, blue and green color scheme, 16:9",
            "Clean celebration graphic with rising bar chart showing website traffic growth, digital marketing agency style, professional flat design, gold and blue colors, 16:9",
        ],
    },
    "tool_trend": {
        "texts": [
            "Google's AI Overviews are changing how local businesses get found.\n\nMore searches now show an AI summary at the top — and those summaries pull from your Google Business Profile, website, and reviews. If your GBP is incomplete or stale, you're invisible in the new AI-driven search.\n\nHuskyTail Digital helps Las Vegas businesses stay ahead of Google's evolving algorithm.",
            "Big GBP update: Google is placing more weight on recent activity when ranking local businesses.\n\nRegular posts, fresh photos, and prompt review responses all signal that your business is active and relevant. Businesses that haven't touched their profile in months are falling behind.\n\nNot sure if your profile is keeping up? Get a free audit from our team.",
            "The local search landscape is shifting. Google now factors in your website's E-E-A-T signals (Experience, Expertise, Authoritativeness, Trust) when ranking your Business Profile.\n\nFor Las Vegas businesses, that means your GBP and website need to work together — consistent messaging, matching categories, aligned content.\n\nWe help businesses build that alignment. Ask us about our local SEO strategy sessions.",
        ],
        "image_prompts": [
            "Futuristic AI search interface graphic showing Google AI Overviews with local business results, modern tech aesthetic, blue neon accents on dark background, 16:9 aspect ratio",
            "Clean infographic showing Google algorithm update timeline with local SEO impact indicators, professional digital marketing style, 16:9",
            "Modern graphic showing AI and local business search integration, clean tech design with Las Vegas skyline silhouette, blue and white color scheme, 16:9",
        ],
    },
    "lead_gen": {
        "texts": [
            "If your business isn't showing up in the top 3 Google Map results for your services, you're invisible to the majority of local searchers.\n\nMost people never scroll past those first results — which means your competitors are capturing leads that should be yours.\n\nWe offer free local visibility audits for Las Vegas, Henderson, and Summerlin businesses. Find out exactly where you stand and what it would take to move up.",
            "Quick question: when did you last Google your own business?\n\nIf you're not on page one of the local map pack, potential customers in Las Vegas are finding your competitors first.\n\nThe good news: local SEO is one of the highest-ROI investments a small business can make. And we'll show you exactly what's holding your ranking back — for free.",
            "Las Vegas has a lot of competition. Standing out in local search isn't optional anymore — it's the difference between a full calendar and an empty one.\n\nOur free GBP audit shows you: where you rank now, what your top competitors are doing differently, and the 3-5 changes that would move the needle fastest.\n\nBook your free audit. No obligation, no pitch.",
        ],
        "image_prompts": [
            "Professional local SEO audit concept graphic showing magnifying glass over Google Maps with Las Vegas pins, clean marketing infographic style, blue and orange accent colors, 16:9 aspect ratio",
            "Clean call-to-action graphic for free local SEO audit with checklist icons, Las Vegas Strip silhouette background, professional digital marketing agency style, 16:9",
            "Modern graphic showing local business visibility gap concept — one business lit up in map results while others fade into background, blue gradient design, 16:9",
        ],
    },
    "brand": {
        "texts": [
            "HuskyTail Digital was built on a simple belief: Las Vegas small businesses deserve the same quality digital marketing that the big brands get.\n\nNo fluff. No vanity metrics. Just strategy that drives real visibility, real leads, and real growth.\n\nOh — and our mascot Everest the husky keeps us humble. 🐾",
            "We started HuskyTail Digital because we kept seeing great local businesses get buried in Google by competitors with worse services and better marketing.\n\nThat's not right. Good businesses deserve to be found.\n\nServing Las Vegas, Henderson, and Summerlin — built on strategy, backed by clarity.",
            "Behind every HuskyTail campaign is a real strategy, not a template.\n\nWe dig into your market, your competitors, and your actual goals before we touch a single setting. That's how we get results that stick.\n\nEverest our husky mascot approves of this approach. 🐾 Las Vegas local SEO done right.",
        ],
        "image_prompts": [
            "Warm professional digital marketing agency brand graphic featuring a friendly Siberian husky mascot alongside clean SEO analytics icons, Las Vegas desert sunset background, blue and warm orange brand colors, 16:9 aspect ratio",
            "Professional agency branding graphic with husky mascot and 'Built on Strategy. Backed by Clarity.' tagline, modern marketing design, desert mountain backdrop, 16:9",
            "Clean agency brand showcase with Siberian husky mascot, digital marketing icons, Las Vegas skyline at dusk, professional and approachable design, 16:9",
        ],
    },
}


def main():
    # ── Load secrets ──────────────────────────────────────────────────────────
    client_id     = os.environ.get("HERMES_GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("HERMES_GOOGLE_CLIENT_SECRET")
    refresh_token = os.environ.get("HERMES_GOOGLE_REFRESH_TOKEN")
    openai_key    = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API")
    github_token  = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")

    for name, val in [
        ("HERMES_GOOGLE_CLIENT_ID", client_id),
        ("HERMES_GOOGLE_CLIENT_SECRET", client_secret),
        ("HERMES_GOOGLE_REFRESH_TOKEN", refresh_token),
        ("OPENAI_API_KEY / OPENAI_API", openai_key),
        ("GITHUB_TOKEN / GITHUB_PAT", github_token),
    ]:
        if not val:
            print(f"[ERROR] Missing env var: {name}")
            sys.exit(1)

    # ── Load state ────────────────────────────────────────────────────────────
    state = load_state(STATE_FILE, STATE_DEFAULTS)

    # ── Dedup guard ───────────────────────────────────────────────────────────
    if not check_dedup(state, guard_hours=20):
        sys.exit(0)

    # ── Select pillar ─────────────────────────────────────────────────────────
    idx = state["pillar_index"] % len(PILLARS)
    pillar = PILLARS[idx]
    content = CONTENT[pillar]

    # Select text and image prompt (cycle within pillar)
    post_num = state["post_counts"].get(pillar, 0)
    text_options = content["texts"]
    img_options  = content["image_prompts"]
    text   = text_options[post_num % len(text_options)]
    prompt = img_options[post_num % len(img_options)]

    # Strip phone numbers
    text = strip_phone_numbers(text)

    print(f"[HuskyTail GMB] Pillar: {pillar} (index {idx}), post #{post_num + 1}")
    print(f"[HuskyTail GMB] Text preview: {text[:80]}...")

    # ── Get access token ──────────────────────────────────────────────────────
    print("[HuskyTail GMB] Refreshing Google access token...")
    token = get_access_token(client_id, client_secret, refresh_token)

    # ── Generate & upload image ───────────────────────────────────────────────
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M")
    filename  = f"gmb-{pillar}-{timestamp}.jpg"
    repo_path = f"{GITHUB_SUBDIR}/{filename}"

    print(f"[HuskyTail GMB] Generating image for pillar '{pillar}'...")
    jpeg_bytes = generate_image(prompt, openai_key)

    print(f"[HuskyTail GMB] Uploading image to GitHub: {repo_path}")
    cdn_url = upload_to_github(
        jpeg_bytes, GITHUB_REPO, repo_path, github_token,
        commit_message=f"HuskyTail GMB image: {filename}"
    )
    print(f"[HuskyTail GMB] CDN URL: {cdn_url}")

    # ── Post to GBP ───────────────────────────────────────────────────────────
    print("[HuskyTail GMB] Posting to Google Business Profile...")
    result = post_to_gbp(
        token=token,
        account_id=ACCOUNT_ID,
        location_id=LOCATION_ID,
        text=text,
        cta_type=CTA_TYPE,
        cta_url=WEBSITE_URL,
        media_url=cdn_url,
    )
    print(f"[HuskyTail GMB] Post created: {result.get('name', 'unknown')}")

    # ── Advance state ─────────────────────────────────────────────────────────
    state["pillar_index"] = (idx + 1) % len(PILLARS)
    state["post_counts"][pillar] = post_num + 1
    record_post(state)
    save_state(STATE_FILE, state)

    print(f"[HuskyTail GMB] Done. Next pillar: {PILLARS[state['pillar_index']]}. State saved.")


if __name__ == "__main__":
    main()
