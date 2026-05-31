def infer_logo_file_extension(image_url: str, content_type: str | None) -> str:
    if content_type:
        content_type_base = content_type.split(";")[0].strip().lower()
        if content_type_base == "image/jpeg":
            return ".jpg"
        if content_type_base == "image/png":
            return ".png"
        if content_type_base == "image/webp":
            return ".webp"
        if content_type_base == "image/gif":
            return ".gif"

    parsed_url = urlparse(image_url)
    url_suffix = Path(parsed_url.path).suffix.strip().lower()
    if url_suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ".jpg" if url_suffix == ".jpeg" else url_suffix
    return ".jpg"