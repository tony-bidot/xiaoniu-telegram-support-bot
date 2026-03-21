import json
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent
FACTS_PATH = BASE_DIR / 'facts.json'


def load_facts() -> Dict[str, Any]:
    return json.loads(FACTS_PATH.read_text(encoding='utf-8'))


def get_recommended_regions() -> List[str]:
    facts = load_facts()
    return facts.get('recommendedRegions', [])


def format_recommended_regions(sep: str = '、') -> str:
    regions = get_recommended_regions()
    return sep.join(regions)


def get_android_facts() -> Dict[str, Any]:
    return load_facts().get('platforms', {}).get('android', {})


def get_ios_facts() -> Dict[str, Any]:
    return load_facts().get('platforms', {}).get('ios', {})


def get_windows_facts() -> Dict[str, Any]:
    return load_facts().get('platforms', {}).get('windows', {})


def get_mac_facts() -> Dict[str, Any]:
    return load_facts().get('platforms', {}).get('mac', {})


def get_vip_facts() -> Dict[str, Any]:
    return load_facts().get('vip', {})


def get_multi_device_limit() -> int:
    return int(load_facts().get('multiDevice', {}).get('maxOnlineDevices', 5))


def get_node_types() -> Dict[str, Any]:
    return load_facts().get('nodeTypes', {})


def get_editions_facts() -> Dict[str, Any]:
    return load_facts().get('editions', {})
