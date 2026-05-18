# Manifest Specification

This document outlines exactly what a `manifest.json` file in a package can include.

## Anatomy

### Required Fields

The manifest file is composed with these basic, yet required building blocks:
```json
{
    "name": "example",
    "description": "An example package",
    "version": "0.42.0",
    "url": "...",
    "sha256": "..."
}
```

The `manifest.json` does not allow any comments.

### Additional Fields

In addition to the above, you can specify fields which are **mutually exclusive** to the `url` and `sha256` fields.

So, instead of the `url` and `sha256` fields, you can specify:

```json
{
    "name": "example",
    "description": "An example package",
    "version": "0.42.0",
    "linux": {
        "url": "...",
        "sha256": "..."
    },
    "macOS": {
        "url": "...",
        "sha256": "..."
    }
}
```
