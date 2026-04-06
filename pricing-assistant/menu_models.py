from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from models import ItemPricingInputs


@dataclass
class MenuProfile:
    menu_name: str
    created_at_iso: str
    items: List[ItemPricingInputs]

    def to_dict(self) -> Dict[str, Any]:
        # Convert ItemPricingInputs objects via __dict__ since they’re dataclasses in your project
        return {
            "menu_name": self.menu_name,
            "created_at_iso": self.created_at_iso,
            "items": [asdict(i) if hasattr(i, "__dataclass_fields__") else i.__dict__ for i in self.items],
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "MenuProfile":
        # Import here to avoid circular imports at runtime
        from models import ItemPricingInputs, Ingredient

        items: List[ItemPricingInputs] = []
        for raw in d.get("items", []):
            # Rehydrate Ingredient dataclasses inside ItemPricingInputs
            ing_list = []
            for ing in raw.get("ingredients", []) or []:
                ing_list.append(Ingredient(**ing))
            raw = dict(raw)
            raw["ingredients"] = ing_list
            items.append(ItemPricingInputs(**raw))

        return MenuProfile(
            menu_name=d.get("menu_name", "Menu"),
            created_at_iso=d.get("created_at_iso", ""),
            items=items,
        )
