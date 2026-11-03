"""Reviewed public facts, not estimated engagement or proof of payment.

Checked 2026-11-02 (America/Chicago). Every positive check names its source.
Instagram observations were read from the matching public page's metadata.
"""

REVIEWED_ON = "2026-11-02"


def source(label, url, kind="seller_page"):
    return {"label": label, "url": url, "kind": kind, "checked_on": REVIEWED_ON}


def observation(note, *sources):
    return {"confirmed": True, "note": note, "sources": list(sources)}


REVIEWS = {
    1: {
        "name": "Anita Dongre", "handle": "anitadongre", "reviewed_on": REVIEWED_ON,
        "followers_label": "2M", "followers_approximate": True, "post_count": 8338,
        "sources": {
            "profile": source("Instagram profile metadata", "https://www.instagram.com/anitadongre/", "public_profile"),
            "store": source("Anita Dongre storefront", "https://us.anitadongre.com/"),
            "contact": source("Anita Dongre contact page", "https://us.anitadongre.com/on/demandware.store/Sites-AD-US-Site/default/ContactUs-Show"),
            "policy": source("Anita Dongre returns and exchanges", "https://us.anitadongre.com/ad-us-customercare/AD-US_return-and-exchange.html"),
            "client": source("Vogue wedding and customization account", "https://www.vogue.com/slideshow/madeleine-kelley-and-amar-singh-wedding", "customer_report"),
        },
        "checks": {
            "profile_public": observation("The public profile identifies the supplied Instagram handle.", "profile"),
            "order_method": observation("The storefront lists clothing, prices and shopping links.", "store"),
            "contact": observation("The business publishes customer-care email, phone and a contact page.", "store", "contact"),
            "terms": observation("A published returns/exchanges policy states conditions and exclusions.", "policy"),
            "outside_reference": observation("Vogue independently publishes a wedding outfit/customization account.", "client"),
            "client_experience": observation("A published client describes working with the team on a customized dupatta. This is not an audited payment record.", "client"),
        },
        "notes": ["Return eligibility varies by item and order; read the seller's current policy."],
    },
    2: {
        "name": "Anu Attires", "handle": "anu_attires", "reviewed_on": REVIEWED_ON,
        "followers_label": "11K", "followers_approximate": True, "post_count": 2285,
        "sources": {
            "profile": source("Instagram profile metadata", "https://www.instagram.com/anu_attires/", "public_profile"),
            "store": source("Anu Attires storefront", "https://www.anuattires.com/"),
            "contact": source("Anu Attires contact page", "https://www.anuattires.com/pages/contact-us"),
            "policy": source("Anu Attires exchanges and returns", "https://www.anuattires.com/pages/exchanges-returns"),
            "credit": source("Gethu Cinema published outfit credit", "https://www.gethucinema.com/2023/12/actress-himaja-hd-photos-and-wallpapers-december-2023.html", "outside_reference"),
        },
        "checks": {
            "profile_public": observation("The public profile identifies the supplied handle and clothing business.", "profile"),
            "order_method": observation("The storefront provides shopping collections and a cart.", "store"),
            "contact": observation("A contact form and customer email are publicly listed.", "contact", "policy"),
            "terms": observation("Published return conditions and exclusions are available.", "policy"),
            "outside_reference": observation("A December 2023 publication credits the supplied handle for an outfit. This historical reference does not prove a sale.", "credit"),
        },
        "notes": ["Custom and sale items may have different return eligibility."],
    },
    5: {
        "name": "The India Craft House", "handle": "theindiacrafthouse", "reviewed_on": REVIEWED_ON,
        "followers_label": "57K", "followers_approximate": True, "post_count": 2452,
        "sources": {
            "profile": source("Instagram profile metadata", "https://www.instagram.com/theindiacrafthouse/", "public_profile"),
            "store": source("The India Craft House storefront", "https://theindiacrafthouse.com/en-us"),
            "policy": source("The India Craft House refund policy and contact details", "https://theindiacrafthouse.com/en-us/policies/refund-policy"),
            "reference": source("India Impact Procurement Network listing", "https://indiaimpactprocurement.org/impact-enterprise-partners", "outside_reference"),
        },
        "checks": {
            "profile_public": observation("The public profile identifies the supplied handle and craft platform.", "profile"),
            "order_method": observation("The storefront provides shopping and custom/bulk-order inquiry links.", "store"),
            "contact": observation("The published policy lists customer email and telephone contact.", "policy"),
            "terms": observation("A published refund policy explains eligibility and notification conditions.", "policy"),
            "outside_reference": observation("An external procurement network lists the named apparel and craft business. This is not a customer review.", "reference"),
        },
        "notes": ["Return requests have notification and eligibility conditions; check the current policy."],
    },
    6: {
        "name": "Klothouse", "handle": "klothouse_official", "reviewed_on": REVIEWED_ON,
        "followers_label": "11K", "followers_approximate": True, "post_count": 1190,
        "sources": {
            "profile": source("Instagram profile metadata", "https://www.instagram.com/klothouse_official/?hl=en", "public_profile"),
            "booking": source("Klothouse Square booking and contact listing", "https://square.site/book/XT4EGH872REZB/klothouse-tailoring-fulshear-tx"),
            "credit": source("BellaNaija Weddings outfit credit", "https://www.bellanaijaweddings.com/asoebibella-wedding-guest-inspo-29/", "outside_reference"),
        },
        "checks": {
            "profile_public": observation("The public profile matches the supplied tailoring handle; the booking page links the same handle.", "profile", "booking"),
            "order_method": observation("The booking page lists consultations, prices and appointment links.", "booking"),
            "contact": observation("The public booking listing supplies business email and telephone contact.", "booking"),
            "terms": observation("The public profile states a no-refund condition. Points indicate disclosure, not favorable terms.", "profile"),
            "outside_reference": observation("A July 2025 BellaNaija Weddings feature credits the supplied handle for an outfit.", "credit"),
        },
        "notes": ["The Instagram profile states no refunds. Confirm the terms before booking."],
    },
    7: {
        "name": "Olis Collections", "handle": "oliscollections", "reviewed_on": REVIEWED_ON,
        "followers_label": "8,921", "followers_approximate": False, "post_count": 1956,
        "sources": {
            "profile": source("Instagram profile metadata", "https://www.instagram.com/oliscollections/", "public_profile"),
            "credit": source("La Mode Magazine outfit/design credit", "https://lamodespot.com/new-cover-alert-la-mode-magazine-58th-edition-featuring-green-october-event-hosts-layole-oyatotun-and-olive-emodi/", "outside_reference"),
        },
        "checks": {
            "profile_public": observation("The public profile identifies OLIS COLLECTIONS and the supplied handle.", "profile"),
            "order_method": observation("The profile directs bookings and inquiries to a listed telephone number, with consultations by appointment.", "profile"),
            "contact": observation("A telephone contact for bookings and inquiries is published in the profile.", "profile"),
            "outside_reference": observation("A September 2020 La Mode Magazine cover credits oliscollections for design/styling. This is historical evidence, not a current sales report.", "credit"),
        },
        "notes": ["Return/cancellation terms and completed-order records were not confirmed in the reviewed sources."],
    },
    8: {
        "name": "Priscer Luxe", "handle": "priscer_luxe", "reviewed_on": REVIEWED_ON,
        "followers_label": "2,463", "followers_approximate": False, "post_count": 625,
        "sources": {
            "profile": source("Instagram profile metadata", "https://www.instagram.com/priscer_luxe/", "public_profile"),
        },
        "checks": {
            "profile_public": observation("The public profile matches the supplied handle. Its display name is African's luxury; legal identity/ownership was not checked.", "profile"),
            "order_method": observation("The profile explicitly instructs shoppers to place orders by direct message.", "profile"),
            "contact": observation("Direct message is explicitly offered as the ordering/contact channel.", "profile"),
            "terms": observation("The public profile states no returns and no refunds. Points indicate disclosure, not favorable terms.", "profile"),
        },
        "notes": ["The profile states no returns and no refunds.", "The reviewed evidence is concentrated in one public profile; no independent customer or transaction evidence was confirmed."],
    },
}
