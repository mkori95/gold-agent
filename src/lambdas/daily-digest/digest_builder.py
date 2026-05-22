from datetime import date, timezone, datetime
from typing import Optional
from src.shared.models.price import PriceSnapshot
from src.shared.models.user import User


def _city_22k(snapshot: PriceSnapshot, city: Optional[str]) -> Optional[float]:
    """Returns 22K per-gram price for user's city if available, else national average."""
    gold = snapshot.metals.get("gold")
    if not gold:
        return None
    if city and gold.city_rates:
        city_key = city.lower().replace(" ", "-")
        raw = gold.city_rates.get(city_key)
        if raw:
            try:
                return round(float(raw) / 10, 0)
            except (ValueError, TypeError):
                pass
    return gold.price_22k_inr


def build_message(user: User, snapshot: PriceSnapshot, diffs: dict, language: str) -> str:
    gold = snapshot.metals.get("gold")
    silver = snapshot.metals.get("silver")
    platinum = snapshot.metals.get("platinum")

    today_str = datetime.now(timezone.utc).strftime("%d %b %Y")
    updated_str = snapshot.timestamp[:16].replace("T", " ") + " UTC" if snapshot.timestamp else "—"
    city_label = user.city or "India avg"

    p22  = f"₹{_city_22k(snapshot, user.city):,.0f}" if _city_22k(snapshot, user.city) else "—"
    p24  = f"₹{gold.price_24k_inr:,.0f}" if gold and gold.price_24k_inr else "—"
    p18  = f"₹{gold.price_18k_inr:,.0f}" if gold and gold.price_18k_inr else "—"

    silver_per_gram = round(silver.price_inr / 31.1035, 0) if silver and silver.price_inr else None
    p_silver = f"₹{silver_per_gram:,.0f}" if silver_per_gram else "—"

    plat_per_gram = round(platinum.price_inr / 31.1035, 0) if platinum and platinum.price_inr else None
    p_plat = f"₹{plat_per_gram:,.0f}" if plat_per_gram else "—"

    yday = diffs.get("yesterday", {})
    week = diffs.get("last_week", {})

    yday_date = yday.get("date", "yesterday")
    week_date = week.get("date", "last week")

    if language == "hi":
        return (
            f"🪙 *Gold Agent — {today_str}*\n"
            f"📍 {city_label}\n\n"
            f"*सोना (प्रति ग्राम)*\n"
            f"  24K: {p24}\n"
            f"  22K: {p22}\n"
            f"  18K: {p18}\n\n"
            f"*चाँदी:* {p_silver}/g\n"
            f"*प्लैटिनम:* {p_plat}/g\n\n"
            f"📊 *बदलाव*\n"
            f"  कल ({yday_date}) से 22K: {yday.get('gold_22k', 'N/A')}\n"
            f"  पिछले हफ्ते ({week_date}) से 22K: {week.get('gold_22k', 'N/A')}\n"
            f"  चाँदी (कल): {yday.get('silver', 'N/A')}\n\n"
            f"🕐 अपडेट: {updated_str}\n\n"
            f"बंद करने के लिए: *stop summary*"
        )
    elif language == "ta":
        return (
            f"🪙 *Gold Agent — {today_str}*\n"
            f"📍 {city_label}\n\n"
            f"*தங்கம் (கிராம் விலை)*\n"
            f"  24K: {p24}\n"
            f"  22K: {p22}\n"
            f"  18K: {p18}\n\n"
            f"*வெள்ளி:* {p_silver}/g\n"
            f"*பிளாட்டினம்:* {p_plat}/g\n\n"
            f"📊 *மாற்றம்*\n"
            f"  நேற்று ({yday_date}) 22K: {yday.get('gold_22k', 'N/A')}\n"
            f"  கடந்த வாரம் ({week_date}) 22K: {week.get('gold_22k', 'N/A')}\n"
            f"  வெள்ளி (நேற்று): {yday.get('silver', 'N/A')}\n\n"
            f"🕐 புதுப்பிக்கப்பட்டது: {updated_str}\n\n"
            f"நிறுத்த: *stop summary*"
        )
    elif language == "te":
        return (
            f"🪙 *Gold Agent — {today_str}*\n"
            f"📍 {city_label}\n\n"
            f"*బంగారం (గ్రాము ధర)*\n"
            f"  24K: {p24}\n"
            f"  22K: {p22}\n"
            f"  18K: {p18}\n\n"
            f"*వెండి:* {p_silver}/g\n"
            f"*ప్లాటినం:* {p_plat}/g\n\n"
            f"📊 *మార్పు*\n"
            f"  నిన్న ({yday_date}) 22K: {yday.get('gold_22k', 'N/A')}\n"
            f"  గత వారం ({week_date}) 22K: {week.get('gold_22k', 'N/A')}\n"
            f"  వెండి (నిన్న): {yday.get('silver', 'N/A')}\n\n"
            f"🕐 అప్‌డేట్: {updated_str}\n\n"
            f"ఆపడానికి: *stop summary*"
        )
    else:
        return (
            f"🪙 *Gold Agent — {today_str}*\n"
            f"📍 {city_label}\n\n"
            f"*Gold (per gram)*\n"
            f"  24K: {p24}\n"
            f"  22K: {p22}\n"
            f"  18K: {p18}\n\n"
            f"*Silver:* {p_silver}/g\n"
            f"*Platinum:* {p_plat}/g\n\n"
            f"📊 *Change*\n"
            f"  vs yesterday ({yday_date}) 22K: {yday.get('gold_22k', 'N/A')}\n"
            f"  vs last week ({week_date}) 22K: {week.get('gold_22k', 'N/A')}\n"
            f"  Silver (vs yesterday): {yday.get('silver', 'N/A')}\n\n"
            f"🕐 Updated: {updated_str}\n\n"
            f"Reply *stop summary* to unsubscribe."
        )
