from pathlib import Path
from typing import List, Tuple
import logging


def check_existing_products(fhr_dir: Path) -> List[str]:
    """Check what products already exist for this forecast hour"""
    if not fhr_dir.exists():
        return []

    existing_files = list(fhr_dir.glob("*_REFACTORED.png"))
    existing_files.extend(list(fhr_dir.glob("**/*_REFACTORED.png")))

    existing_products = []
    for file_path in existing_files:
        parts = file_path.stem.split("_")
        if len(parts) >= 3 and parts[-1] == "REFACTORED":
            product_name = "_".join(parts[:-2])
            existing_products.append(product_name)

    return list(set(existing_products))


def get_missing_products(fhr_dir: Path, all_products: List[str]) -> Tuple[List[str], List[str]]:
    """Get list of products that haven't been generated yet"""
    existing = check_existing_products(fhr_dir)
    missing = [p for p in all_products if p not in existing]
    return missing, existing


def get_available_products() -> List[str]:
    """Get all available products from the field registry"""
    try:
        from field_registry import FieldRegistry
        registry = FieldRegistry()
        all_fields = registry.get_all_fields()
        return list(all_fields.keys())
    except Exception as e:
        logging.getLogger(__name__).error(f"Could not load field registry: {e}")
        return []