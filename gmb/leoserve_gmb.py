#!/usr/bin/env python3
"""
LeoServe GMB Posting Script
Schedule: every 3 days at 9am ET (0 14 */3 * * UTC)
Pillar rotation: emergency_cta → salt_air_marine → service_spotlight → trust_social_proof → local_seasonal
Service area rotation independent of pillars.
"""

import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(__file__))
from gmb_post_lib import (
    get_access_token, post_to_gbp, strip_phone_numbers,
    check_dedup, record_post, load_state, save_state,
    generate_image, upload_to_github,
)

# ── Config ────────────────────────────────────────────────────────────────────

ACCOUNT_ID  = "115031750744438008488"
LOCATION_ID = "4023026853355266882"
WEBSITE_URL = "http://leoservecleaning.com"
CTA_TYPE    = "CALL"

GITHUB_REPO   = "stephen-huskytail/automation411"
GITHUB_SUBDIR = "gmb/leoserve"

STATE_FILE = os.path.join(os.path.dirname(__file__), "state_leoserve.json")

STATE_DEFAULTS = {
    "pillar_index": 0,
    "area_index": 0,
    "post_counts": {},
    "last_post": None,
}

PILLARS = [
    "emergency_cta",
    "salt_air_marine",
    "service_spotlight",
    "trust_social_proof",
    "local_seasonal",
]

SERVICE_AREAS = [
    "Key West",
    "Stock Island",
    "Marathon",
    "Islamorada",
    "Key Largo",
    "Big Pine Key",
    "Cudjoe Key",
    "Summerland Key",
    "Tavernier",
    "Plantation Key",
]

# ── Content templates ─────────────────────────────────────────────────────────
# Each text uses {area} as a placeholder for the current service area.

CONTENT = {
    "emergency_cta": {
        "texts": [
            "Your car, your driveway, your schedule. LeoServe comes to YOU in {area}.\n\nNo drop-offs. No waiting rooms. Just a sparkling clean vehicle while you get on with your day. We run 7 days a week so your car never has to wait for a clean.\n\nMobile car wash and auto detailing — serving the entire Florida Keys.",
            "Busy week in {area}? Your car doesn't have to look like it.\n\nLeoServe is fully mobile — we bring the wash to wherever you are. Book for home, work, or anywhere in between. 7 days a week, no appointment too last-minute.\n\nThe Keys' premier mobile auto detailing service. Call to schedule.",
            "Life in the Keys moves fast. Your car care shouldn't slow you down.\n\nLeoServe mobile detailing comes to you in {area} — professional-grade wash, wax, and interior detail without you ever leaving your property. We're available 7 days a week.\n\nCall to book your mobile detail today.",
        ],
        "image_prompts": [
            "Professional mobile car detailing service photo — detailer washing a clean bright vehicle in a residential driveway in the Florida Keys, palm trees and blue sky background, vibrant and professional, 16:9 aspect ratio",
            "Mobile auto detailing van parked by a sparkling clean luxury SUV in a tropical Florida setting, professional service aesthetic, blue and white brand colors, 16:9",
            "Detailer applying finishing wax to a black car in a Key West-style neighborhood, tropical greenery background, professional mobile car care service visual, 16:9",
        ],
    },
    "salt_air_marine": {
        "texts": [
            "Living in {area} is incredible. But the salt air and UV exposure down here are brutal on your car's paint.\n\nWithout protection, oxidation and clear coat damage start faster than you'd expect. Ceramic coating creates a permanent barrier between your paint and the Florida Keys environment.\n\nLeoServe offers professional ceramic coating that lasts years — not weeks. Call for a free quote.",
            "The Florida Keys sun in {area} isn't just hot — it's relentless. UV rays break down your car's clear coat, fade paint, and cause oxidation that's expensive to reverse.\n\nCeramic coating is the smartest protection you can give your vehicle in this climate. Hard shell barrier. Hydrophobic finish. Years of protection from one application.\n\nLeoServe — Keys-specialized auto detailing and ceramic coating.",
            "Salt spray from {area}'s waterways does more damage to car paint than most people realize. Over time, it etches into the clear coat and causes rust on metal surfaces.\n\nOur ceramic coating seals out salt, moisture, and UV — the three biggest threats to your vehicle in the Florida Keys.\n\nCall LeoServe for a ceramic coating consultation. We serve the entire Keys.",
        ],
        "image_prompts": [
            "Dramatic before-and-after graphic showing dull oxidized car paint vs gleaming ceramic-coated finish, Florida Keys ocean backdrop, professional auto detailing marketing image, 16:9 aspect ratio",
            "Close-up macro photo of ceramic coating hydrophobic water beading on dark blue car paint, tropical Florida setting, premium auto care aesthetic, 16:9",
            "Split composition showing salt air and ocean spray alongside a protected gleaming vehicle with ceramic coating, Florida Keys setting, professional detailing advertisement style, 16:9",
        ],
    },
    "service_spotlight": {
        "texts": [
            "What does a full LeoServe auto detail actually include?\n\n✓ Exterior hand wash + clay bar decontamination\n✓ Tire and wheel cleaning\n✓ Interior vacuum + surface wipe-down\n✓ Dashboard, console, and door panel treatment\n✓ Glass cleaning inside and out\n✓ Final detail inspection\n\nAll done at your location in {area}. No need to drive anywhere. Call to schedule.",
            "Ceramic coating from LeoServe isn't just a wax. It's a professional-grade nano-coating that chemically bonds to your paint.\n\nBenefits:\n✓ 9H hardness rating — scratch resistance\n✓ Hydrophobic — water and dirt bead off\n✓ UV protection against Florida Keys sun\n✓ Chemical resistance\n✓ Lasts 3-5 years with proper maintenance\n\nServing {area} and the entire Florida Keys. Call for a ceramic coating quote.",
            "Full detailing or ceramic coating — LeoServe does both, at your location in {area}.\n\nWe also handle: window cleaning, house pressure washing, and boat and airplane detailing.\n\nIf it needs cleaning and you're in the Keys, we've got it covered. Call to schedule your service.",
        ],
        "image_prompts": [
            "Professional auto detailing service checklist infographic with clean modern design, tropical Florida Keys color palette, teal and white, detailing icons, 16:9 aspect ratio",
            "Detailer professionally cleaning and polishing a white BMW convertible in a Florida Keys waterfront setting, high-end auto care aesthetic, 16:9",
            "Clean product comparison graphic showing standard car wash vs full ceramic coating protection, professional marketing design, ocean blue and white theme, 16:9",
        ],
    },
    "trust_social_proof": {
        "texts": [
            "LeoServe holds a 5.0-star rating — and every single review is 5 stars.\n\nThat's not luck. That's what happens when you treat every car in {area} like it's your own. We take mobile detailing seriously because your vehicle deserves it.\n\nJoin our growing list of happy customers across the Florida Keys. Call to book.",
            "Every LeoServe review is 5 stars. Not most of them — all of them.\n\nCustomers in {area} trust us because we show up on time, we do the work right, and we don't cut corners. Mobile auto detailing and ceramic coating done by specialists who care.\n\nSee our reviews and book your detail today.",
            "Auto detailing specialists with a perfect 5.0-star record across the Florida Keys.\n\nFrom quick mobile washes to full ceramic coating applications in {area}, our customers keep coming back because the results speak for themselves. Every review tells the same story: LeoServe delivers.\n\nCall to experience it yourself.",
        ],
        "image_prompts": [
            "5-star review showcase graphic with gold stars and satisfied customer testimonial quotes, tropical Florida Keys background, professional auto detailing service branding, 16:9 aspect ratio",
            "Clean trust badge graphic showing 5.0 star rating with review count, professional service industry style, ocean turquoise and gold color scheme, 16:9",
            "Professional auto detailer shaking hands with happy customer in front of a gleaming freshly-detailed vehicle in a Keys neighborhood, trust and quality visual, 16:9",
        ],
    },
    "local_seasonal": {
        "texts": [
            "Summer in the Keys is beautiful — and absolutely punishing on car paint.\n\nBetween the UV index, the heat, and the salt air in {area}, your car's exterior takes more abuse in one summer than most mainland cars see in 5 years.\n\nThis is exactly when a ceramic coating investment pays for itself. LeoServe applies professional-grade protection that keeps your paint looking new through every Keys summer.",
            "Hot cars + Florida humidity = a nightmare for interiors.\n\nIn {area}, the summer heat bakes vinyl dashboards, fades fabric, and cracks leather if left unprotected. A regular interior detail removes buildup and protects surfaces before the damage sets in.\n\nLeoServe mobile detailing brings the solution to your driveway. Book a summer detail today.",
            "Keys climate is unique — and so is your car's maintenance needs in {area}.\n\nBetween the bridges and open water, vehicles down here see constant salt exposure that accelerates corrosion and paint damage. Our Florida Keys-specialized detail packages address exactly these conditions.\n\nLeoServe knows the Keys because we live here. Call for seasonal car care that actually fits where you live.",
        ],
        "image_prompts": [
            "Bright Florida Keys summer landscape with a spotlessly clean detail vehicle parked by the water, tropical sky and turquoise ocean, vibrant summer car care aesthetic, 16:9 aspect ratio",
            "Professional mobile detailer working on a vehicle in intense Florida sunshine, showing protection and care against harsh UV, Keys beachside setting, 16:9",
            "Clean seasonal promotion graphic showing summer sun and tropical heat icons alongside a ceramic-coated gleaming vehicle, Florida Keys aesthetic, teal and orange, 16:9",
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

    # ── Select pillar + area ──────────────────────────────────────────────────
    pillar_idx = state["pillar_index"] % len(PILLARS)
    area_idx   = state["area_index"] % len(SERVICE_AREAS)
    pillar     = PILLARS[pillar_idx]
    area       = SERVICE_AREAS[area_idx]
    content    = CONTENT[pillar]

    post_num = state["post_counts"].get(pillar, 0)
    text_raw = content["texts"][post_num % len(content["texts"])]
    prompt   = content["image_prompts"][post_num % len(content["image_prompts"])]

    # Inject area and strip phone numbers
    text = strip_phone_numbers(text_raw.format(area=area))

    print(f"[LeoServe GMB] Pillar: {pillar} | Area: {area}")
    print(f"[LeoServe GMB] Text preview: {text[:80]}...")

    # ── Get access token ──────────────────────────────────────────────────────
    print("[LeoServe GMB] Refreshing Google access token...")
    token = get_access_token(client_id, client_secret, refresh_token)

    # ── Generate & upload image ───────────────────────────────────────────────
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M")
    filename  = f"leoserve-{pillar}-{timestamp}.jpg"
    repo_path = f"{GITHUB_SUBDIR}/{filename}"

    print(f"[LeoServe GMB] Generating image for pillar '{pillar}'...")
    jpeg_bytes = generate_image(prompt, openai_key)

    print(f"[LeoServe GMB] Uploading to GitHub: {repo_path}")
    cdn_url = upload_to_github(
        jpeg_bytes, GITHUB_REPO, repo_path, github_token,
        commit_message=f"LeoServe GMB image: {filename}"
    )
    print(f"[LeoServe GMB] CDN URL: {cdn_url}")

    # ── Post to GBP ───────────────────────────────────────────────────────────
    print("[LeoServe GMB] Posting to Google Business Profile...")
    result = post_to_gbp(
        token=token,
        account_id=ACCOUNT_ID,
        location_id=LOCATION_ID,
        text=text,
        cta_type=CTA_TYPE,
        cta_url=None,  # CALL CTA — no URL
        media_url=cdn_url,
    )
    print(f"[LeoServe GMB] Post created: {result.get('name', 'unknown')}")

    # ── Advance state ─────────────────────────────────────────────────────────
    state["pillar_index"] = (pillar_idx + 1) % len(PILLARS)
    state["area_index"]   = (area_idx + 1) % len(SERVICE_AREAS)
    state["post_counts"][pillar] = post_num + 1
    record_post(state)
    save_state(STATE_FILE, state)

    print(f"[LeoServe GMB] Done. Next: pillar={PILLARS[state['pillar_index']]}, area={SERVICE_AREAS[state['area_index']]}.")


if __name__ == "__main__":
    main()
