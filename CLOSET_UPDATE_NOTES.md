# Saved Closet

Buyers can save pieces from Discover, featured Home cards, seller collection
cards, and item pages. Their private `/closet` lists the most recently saved
pieces first, supports removal, and shows a saved count or an empty state.
My Account and the main navigation link to the closet. Sellers cannot use
buyer closet endpoints; guests receive Log in to save links.

## Storage and ownership

The feature uses the original `saveditems` table, its unique `(user_id,
item_id)` key, and its foreign keys. There is no migration or dependency.
All reads and writes use the authenticated user's database ID. Submitted
user IDs and saved-row IDs are ignored. Mutations recheck the buyer role in
a transaction and lock that user's row, then insert/delete only that user's
item pair. Explicit save/remove actions are idempotent and retain the
original save date on repeat saves. Failed writes roll back. Removing a save
does not delete the catalog item.

## Routes and interface

- GET `/closet`: the buyer's collection or a friendly unavailable message.
- POST `/closet/items/<product_id>/save`: save an existing catalog piece.
- POST `/closet/items/<product_id>/remove`: remove an owned save.
- State-changing forms retain the existing CSRF protection and POST-only
  behavior. Signed-in responses retain `Cache-Control: no-store`.
- Save controls load the buyer's saved IDs once per rendered request, rather
  than querying for every clothing card. A failed state read leaves browsing
  usable and disables its save buttons instead of guessing their state.
- The shared product query formats closet cards consistently with Discover.
  Server-side seller/item links, photos, price notes, and sizes are retained.
- JavaScript submits existing forms, confirms the returned state, and updates
  button feedback and counts without reloading. Pending requests prevent
  duplicate submissions for a piece. Removal preserves keyboard focus and
  respects reduced-motion preferences. A mismatch caused by another tab's
  changes refreshes the collection from the server.
- Interrupted responses show a refresh message instead of assuming a write
  succeeded. No POST is retried automatically. Native HTML forms still work,
  preserving allowed local catalog/filter paths and piece anchors. External
  redirect targets are rejected.

## Package

This is part of the cumulative CultureLink_Accounts_Update.zip. Replace all
included files, including app.py, and restart Spyder's kernel. The working
animated account/profile flow is included. Connection settings, original SQL,
photos, session keys, fixtures, and private account data are excluded.

New source: `services/closet.py`, `routes/closet.py`, `templates/closet.html`,
`static/closet.css`, and `static/closet.js`. Shared card templates, the base
navigation/assets, account link, item actions, and app registration are updated.

## Validation

13 closet integration tests and the 24 existing account/profile tests passed.
The closet checks cover private ownership, role restrictions, duplicate saves
and removals, persistence, sort order, CSRF, POST-only mutation, unknown IDs,
local return paths, transactional rollback, and unavailable storage.

The supplied catalog regression passed for 31 items, six curated sellers,
19 filter cases, six directory cases, local photos, and 44 navigation targets.
Browser checks covered the closet and both account roles at 1440, 768, 375,
and 320 pixels, loading feedback, no-reload save/remove, keyboard focus,
reduced motion, account isolation, logout/login, response interruption, and
the complete no-JavaScript flow. The existing animated setup checks were
also run. Desktop and phone screenshots were visually inspected.

These checks use a temporary SQLite database with an adapter for the supplied
MySQL schema and queries. They are not a live MySQL test. The installation
notes give the final checks on the user's Windows computer.

## References

- [MySQL locking reads](https://dev.mysql.com/doc/refman/8.0/en/innodb-locking-reads.html)
- [Flask request handling](https://flask.palletsprojects.com/en/stable/tutorial/views/)
