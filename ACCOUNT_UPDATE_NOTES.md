# Buyer and seller account setup

The current cumulative package also includes the private Saved Closet.
See `CLOSET_UPDATE_NOTES.md` for its behavior and validation, and use the
current `START_HERE.txt` installation instructions for the complete update.

After registration, CultureLink signs the new account in and opens a modal
with two cards: Buyer and Seller. Selecting a card opens the corresponding
profile form. Saving creates the profile and leads to My Account, where that
profile can be edited. Login/logout, hashes, CSRF protection, and independent
sessions remain part of the account flow.

## Animated setup update

The setup forms progressively submit with Fetch and render the server's
next HTML page inside the existing document. The loading button leads into
a fading backdrop and a gently rising role dialog. The welcome check draws
in and the cards appear in sequence. Choosing a card highlights it, shows a
check, dims the other card, and transitions into its profile form. Saving a
profile transitions into My Account. The shared header and CSRF form update
from the server response when the user becomes signed in.

The enhancement sends the existing CSRF-protected forms to the existing
routes. It adds no API, account fields, SQL, dependencies, or server changes.
Required fields and server validation remain authoritative. Returned errors
receive focus and the replacement forms retain their server-rendered values.
Password visibility controls also work after a validation response.

Duplicate submit events are blocked while a request is pending. A failed or
timed-out response offers a GET link to continue from My Account, without
automatically repeating a POST that may already have saved. Back/Forward
and refresh resolve the current server state. Passwords and HTML snapshots
are not saved into browser history or local/session storage.

The native dialog retains keyboard focus and Escape/reopen controls.
Reduced-motion preferences turn off movement, and lack of the animation API
does not stop setup. Without JavaScript, the original form/redirect flow
still works. Versioned asset links load the new scripts and styles.

For an installation where profiles already work, replace only `templates/`
and `static/`, then refresh the browser. The SQL migration is only needed
once when adding profile storage to a new local database.

## Flow and ownership

- New registrations start with `users.role = pending`.
- Buyer selection stores the existing `customer` role; Seller stores `seller`.
- Only those two choices are accepted. Role selection cannot grant admin.
- Incomplete accounts can change their choice. A completed profile keeps its
  type. Old customer accounts without a profile can choose either type.
- Profile routes require login and the matching database role. User and seller
  IDs in submitted forms do not determine ownership.
- Role/profile writes lock the account row and use one transaction for each
  save. Database failures roll back partial writes.
- Seller onboarding creates a new owned seller record. It does not let an
  account claim or edit the six existing curated seller records.

## Database changes

Run `sql/02_buyer_seller_profiles.sql` once per local database before using
profile setup. It creates `buyer_profiles` and `seller_profiles` if absent.
There are no destructive statements or changes to existing table structures.
Existing accounts and the 31 products are preserved.

Addresses reuse the existing `locations` and `userlocations` tables. Saving
replaces only the current account's default address. A shared address row is
not edited for other users. Unreferenced replaced addresses are removed.
Buyer measurements, preferences, and contact information are stored in the
buyer profile. Seller contact information and the owned seller ID are stored
in the seller profile. New sellers start with `verification_status=unreviewed`.

## Public and private fields

Seller pages use a specific public-field query. They show business name,
description, website/social page, city/region/country, cultures, occasions,
clothing types, lead time, price guidance, and delivery areas. Private contact
name, phone, account email, street address, and postal code are excluded.
Buyer profile details are available only on that buyer's protected pages.
Seller-directory culture filters also recognize cultures supplied in a new
seller profile, including profiles with no clothing listings yet.

## Files

| File | Purpose |
| --- | --- |
| `app.py` | Registers authentication and profile routes; keeps Spyder's password prompt and disabled reloader. |
| `routes/auth.py` | Creates a pending account, starts its session, sends it to the role popup, and resolves My Account to its profile. |
| `routes/onboarding.py` | Role selection and the two protected profile forms. |
| `services/accounts.py` | Existing users-table queries, now with pending registration. |
| `services/profiles.py` | Owned profiles, transactional saves, address handling, and public seller metadata. |
| `services/profile_validation.py` | Required fields, limits, units, measurements, addresses, and HTTP(S) links. |
| `services/account_security.py` | Existing session/form security and attempt tracking; form size limit increased to 128 KiB for profiles. |
| `services/boutiques.py` | Combines public profile details with existing catalog details. |
| `templates/onboarding/` | Role dialog, Buyer form, Seller form, and shared field macros. |
| `templates/auth/` | Authentication pages and updated account summary. |
| `templates/base.html` | Shared account/profile assets and account navigation. |
| `templates/boutique_details.html` | Displays public lead times, price guidance, and delivery areas. |
| `static/profiles.css`, `static/profiles.js` | Responsive role cards, profile layouts, and native dialog enhancement. |
| `static/accounts.css`, `static/accounts.js` | Existing account styling, password visibility, and error-summary focus. |
| `sql/02_buyer_seller_profiles.sql` | The two new profile tables. |
| `.gitignore`, `requirements.txt` | Existing dependency setup and local-key exclusion. |

This is a cumulative update for the current Home/Discover/browsing project.
It includes all account files from the previous account package. It excludes
`config.py`, `database.py`, photos, generated session keys, and account data.

## Validation

24 integration/security tests passed, covering both role paths, persistence,
validation, role restrictions, account isolation, address isolation/removal,
private seller data, safe public links, fixed login destinations, role/ID
spoofing, duplicate emails, wrong passwords, session tampering, CSRF checks,
transaction rollback, attempt limits, and oversized forms.

Catalog regression checks passed for all 31 item pages, all 6 existing seller
collections, 19 catalog filter cases, 6 seller-directory cases, local photos,
and 44 internal navigation targets.

Browser checks passed at 1440, 768, 375, and 320 pixels: immediate modal after
registration, both profile forms, saved profiles and edits, logout/login,
private seller-data checks, Escape/reopen, keyboard focus containment, and
no JavaScript errors or horizontal overflow. The full buyer setup also
works without JavaScript. Desktop and phone screenshots were visually checked.

Additional motion checks cover signup, role selection, profile validation,
and profile saving in the same document; duplicate-submit prevention;
loading and selected-card states; updated signed-in navigation; registration
errors and password controls; Back/Forward and refresh; lost-response
recovery without a POST retry; reduced motion; and missing animation API.

These are tests against a temporary SQLite fixture and a MySQL-query adapter
based on the supplied schema, including the two new tables. They are not a
live MySQL test. The installation guide gives the final MySQL checks to run
on the user's Windows computer.

## Account security retained

Werkzeug scrypt hashes; 12–128-character passwords; unique normalized email
addresses; signed, fresh login sessions; HttpOnly and SameSite=Lax cookies;
12-hour sessions; POST-only logout; CSRF-protected state-changing forms;
no-store responses for signed-in pages; and per-process attempt limits.
A random local session key is generated in ignored `instance/session.key`;
a configured non-default key is preserved. Local HTTP keeps Secure cookies
off; a future HTTPS deployment should enable `SESSION_COOKIE_SECURE`.
Attempt tracking is process-local, resets on restart, and is not a shared
hosting rate-limit service. Seller review and listing management can be
added using the owned `seller_profiles.seller_id` relationship.

## References

- [Flask authentication](https://flask.palletsprojects.com/en/stable/tutorial/views/)
- [Werkzeug password hashing](https://werkzeug.palletsprojects.com/en/stable/utils/#werkzeug.security.generate_password_hash)
- [Native HTML dialog](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog)
- [Element animations](https://developer.mozilla.org/en-US/docs/Web/API/Element/animate)
- [MySQL locking reads](https://dev.mysql.com/doc/refman/8.0/en/innodb-locking-reads.html)
- [MySQL CREATE TABLE](https://dev.mysql.com/doc/refman/8.0/en/create-table.html)
