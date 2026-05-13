"""Perceptual hash (dHash) based image deduplication."""

from typing import List

import cv2
import numpy as np
import os

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}


def compute_dhash(image_path: str) -> str:
    """Compute a 64-bit difference hash for the image at *image_path*.

    Returns a 64-character binary string, or ``""`` when the image cannot
    be loaded.
    """
    img = cv2.imread(image_path)
    if img is None:
        return ""

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (9, 8))

    bits: List[str] = []
    for row in resized:
        for i in range(8):
            bits.append('1' if row[i + 1] > row[i] else '0')

    return ''.join(bits)


def hamming_distance(hash1: str, hash2: str) -> int:
    """Return the Hamming distance between two dHash strings.

    If the strings differ in length, 65 is returned (larger than any
    valid 64-bit distance).
    """
    if len(hash1) != len(hash2):
        return 65
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))


def dedup_by_dhash(image_paths: List[str], threshold: int = 5) -> List[str]:
    """Return a de-duplicated list of *image_paths* using dHash similarity.

    An image is kept only when its hash is at least *threshold* bits away
    from every already-kept image.  Files outside *SUPPORTED_EXTENSIONS*
    or that fail to load are silently skipped.
    """
    filtered = [
        p for p in image_paths
        if os.path.splitext(p)[1].lower() in SUPPORTED_EXTENSIONS
    ]

    kept_paths: List[str] = []
    kept_hashes: List[str] = []

    for path in filtered:
        h = compute_dhash(path)
        if not h:
            continue
        if any(hamming_distance(h, kh) < threshold for kh in kept_hashes):
            continue
        kept_paths.append(path)
        kept_hashes.append(h)

    return kept_paths


if __name__ == "__main__":
    import sys

    h1 = compute_dhash(__file__)
    assert isinstance(h1, str), f"compute_dhash returned {type(h1)}"
    print(f"dhash of this file: {h1 or '(could not load as image)'}")

    dist = hamming_distance("0" * 64, "1" * 64)
    assert dist == 64, f"Expected 64, got {dist}"
    dist_same = hamming_distance("0" * 64, "0" * 64)
    assert dist_same == 0, f"Expected 0, got {dist_same}"
    dist_diff_len = hamming_distance("0", "00")
    assert dist_diff_len == 65, f"Expected 65 for diff-len, got {dist_diff_len}"

    print("hamming_distance: all assertions passed")

    result = dedup_by_dhash([])
    assert result == [], f"Expected empty list, got {result}"

    print("dedup_by_dhash: all assertions passed")
    print("Basic import & smoke test passed!")
