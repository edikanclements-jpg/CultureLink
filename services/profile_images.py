"""Optional account pictures, stored outside the public static folder.

Only the current account can write its images. Buyer images have no public URL;
seller logos/portraits are published through the matching seller profile.
"""

from io import BytesIO
import json
import os
from pathlib import Path
import re
import tempfile
from threading import RLock
import warnings
import hashlib

from flask import current_app, has_request_context, url_for
from services.catalog_rules import LOCATION_OVERRIDES

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000
KINDS = {"avatar", "logo", "portrait"}
_WRITE_LOCK = RLock()
_IMAGE_NAME = re.compile(r"[a-f0-9]{64}\.png")
CURATED_IMAGE_FILES = {
    1: {"logo": "1-logo.png", "portrait": "1-portrait.jpg"},
    2: {"logo": "2-logo.png", "portrait": "2-portrait.jpg"},
    5: {"logo": "5-logo.jpg", "portrait": "5-portrait.png"},
    6: {"logo": "6-logo.png", "portrait": "6-portrait.png"},
    7: {"logo": "7-logo.png", "portrait": "7-portrait.png"},
    8: {"logo": "8-logo.png", "portrait": "8-portrait.png"},
}
CURATED_OWNER_DETAILS = {
    2: ("Mrs. Anu", "Owner"),
    5: ("Sona Puri", "CEO"),
    6: ("Vickie Jo", "Owner"),
    7: ("Olaide Ofolis", "Owner"),
    8: ("Mrs. Priscer", "Owner"),
}


class PhotoValidationError(ValueError):
    pass


def _directory(user_id):
    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
        raise ValueError("A valid account is required.")
    return Path(current_app.instance_path) / "profile-images" / ("user-" + str(user_id))


def _manifest(directory):
    try:
        value = json.loads((directory / "pictures.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (ValueError, UnicodeError) as error:
        raise OSError("The saved picture list could not be read.") from error
    if not isinstance(value, dict) or value.get("format") != 1 or not isinstance(value.get("images"), dict):
        raise OSError("The saved picture list could not be read.")
    return {kind: name for kind, name in value["images"].items()
            if kind in KINDS and isinstance(name, str) and _IMAGE_NAME.fullmatch(name)}


def image_path(user_id, kind):
    if kind not in KINDS:
        return None
    directory = _directory(user_id)
    name = _manifest(directory).get(kind)
    if name:
        path = directory / name
        if path.is_file():
            return path
    return None


def account_images(user_id, role):
    kinds = ("avatar",) if role == "customer" else ("logo", "portrait") if role == "seller" else ()
    result = {}
    for kind in kinds:
        path = image_path(user_id, kind)
        if path:
            result[kind] = url_for("auth.account_image", kind=kind, v=path.stem)
    return result


def public_seller_images(seller_id, user_id=None, seller_name=""):
    if not has_request_context():
        return {}
    result = {}
    expected_name = LOCATION_OVERRIDES.get(seller_id, ("", ""))[0]
    curated_matches = bool(expected_name and expected_name.casefold() == str(seller_name).strip().casefold())
    for kind in ("logo", "portrait"):
        # Original team-provided files keep their actual PNG/JPEG encoding.
        # Existing curated businesses are never claimed by a new seller account.
        filename = CURATED_IMAGE_FILES.get(seller_id, {}).get(kind)
        curated = Path(current_app.static_folder) / "branding" / "sellers" / filename if filename else None
        path = image_path(user_id, kind) if user_id is not None else None
        if path:
            result[kind] = url_for("boutiques.boutique_image", boutique_id=seller_id, kind=kind, v=path.stem)
        elif curated_matches and curated is not None and curated.is_file():
            result[kind] = url_for("static", filename="branding/sellers/" + curated.name, v=curated.stat().st_mtime_ns)
    if curated_matches and seller_id in CURATED_OWNER_DETAILS:
        result["owner_name"], result["owner_role"] = CURATED_OWNER_DETAILS[seller_id]
    return result


def initials(name):
    words = re.findall(r"[^\W_]+", str(name or ""), re.UNICODE)
    return "".join(word[0] for word in words[:2]).upper() or "CL"


def _clean_image(upload):
    from PIL import Image, ImageOps, UnidentifiedImageError

    data = upload.stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise PhotoValidationError("Choose a picture smaller than 5 MB.")
    if not data:
        raise PhotoValidationError("That picture is empty. Choose another file.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data), formats=("PNG", "JPEG", "WEBP")) as check:
                if check.width * check.height > MAX_PIXELS or max(check.size) > 12000:
                    raise PhotoValidationError("Choose a picture of 20 megapixels or fewer.")
                if getattr(check, "n_frames", 1) != 1:
                    raise PhotoValidationError("Choose a still picture in PNG, JPG, or WebP format.")
                check.verify()
            with Image.open(BytesIO(data), formats=("PNG", "JPEG", "WEBP")) as source:
                source.load()
                oriented = ImageOps.exif_transpose(source)
                oriented.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                pixels = oriented.convert("RGBA")
                # A fresh image carries no GPS, EXIF, comments, or source metadata.
                clean = Image.new("RGBA", pixels.size)
                clean.paste(pixels)
                output = BytesIO()
                clean.save(output, format="PNG", optimize=True)
                return output.getvalue()
    except PhotoValidationError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise PhotoValidationError("Choose a readable PNG, JPG, or WebP picture.") from error


def prepare_images(files, form, kinds):
    changes, errors = {}, {}
    for kind in kinds:
        field = "photo_" + kind
        uploads = [upload for upload in files.getlist(field) if upload.filename]
        if len(uploads) > 1:
            errors[field] = "Choose one picture for this space."
        elif uploads:
            try:
                changes[kind] = _clean_image(uploads[0])
            except PhotoValidationError as error:
                errors[field] = str(error)
        elif form.get("remove_" + kind) == "1":
            changes[kind] = None
    return changes, errors


def _atomic_write(path, data):
    descriptor, temporary = tempfile.mkstemp(prefix=".picture-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def save_images(user_id, changes):
    if not changes:
        return
    if set(changes) - KINDS:
        raise ValueError("Unknown picture space.")
    directory = _directory(user_id)
    with _WRITE_LOCK:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        images = _manifest(directory)
        for kind, data in changes.items():
            if data is None:
                images.pop(kind, None)
            else:
                name = hashlib.sha256(data).hexdigest() + ".png"
                _atomic_write(directory / name, data)
                images[kind] = name
        # All files exist before one atomic pointer change publishes the set.
        _atomic_write(directory / "pictures.json", json.dumps({"format": 1, "images": images}).encode("utf-8"))
        for path in directory.glob("*.png"):
            if path.name not in images.values():
                try:
                    path.unlink()
                except OSError:
                    pass  # Windows may still have an earlier image response open.
