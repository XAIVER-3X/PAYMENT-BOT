import logging

import aiohttp

from db import get_rewarble_api_key

log = logging.getLogger(__name__)


async def verify_rewarble_code(code):
    api_key = get_rewarble_api_key()
    if not api_key:
        log.warning("REWARBLE API KEY NOT SET. Use /setapikey to configure.")
        return False, "⚠️ Payment verification is temporarily unavailable. Please contact support.", None

    url = "https://api.rewarble.com/client/1.00/redeem"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"code": code}

    masked_key = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
    log.info(f"REWARBLE REQUEST | url={url} | key={masked_key} | code={code}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload,
                                    timeout=aiohttp.ClientTimeout(total=10)) as resp:
                raw_text = await resp.text()
                log.info(f"REWARBLE RESPONSE | status={resp.status} | body={raw_text}")

                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    if "faceValue" in data and "voucherSerial" in data:
                        return True, "✅ Code verified successfully!", data
                    error_msg = data.get("message", "Invalid code or already redeemed")
                    return False, f"❌ {error_msg}", data

                return False, "❌ Payment verification failed. Please contact support.", None
    except Exception as e:
        log.error(f"Rewarble API exception: {e}")
        return False, "⚠️ Network error. Please try again later or contact support.", None
