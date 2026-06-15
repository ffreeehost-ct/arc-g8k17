import random
import string
from math import ceil


def generate_promo_code(prefix='TG'):
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=6))
    return f'{prefix}-{suffix}'


def format_price(price_usd):
    return f'{price_usd:.2f}$'


def paginate(items, page, per_page=12):
    total = len(items)
    start = page * per_page
    end = start + per_page
    return items[start:end], ceil(total / per_page), page


def get_flag(code):
    flags = {
        'US': '🇺🇸', 'RU': '🇷🇺', 'KZ': '🇰🇿', 'UA': '🇺🇦', 'DE': '🇩🇪',
        'FR': '🇫🇷', 'GB': '🇬🇧', 'IT': '🇮🇹', 'ES': '🇪🇸', 'CA': '🇨🇦',
        'CN': '🇨🇳', 'JP': '🇯🇵', 'KR': '🇰🇷', 'IN': '🇮🇳', 'BR': '🇧🇷',
        'TR': '🇹🇷', 'AE': '🇦🇪', 'PL': '🇵🇱', 'NL': '🇳🇱', 'SG': '🇸🇬',
        'HK': '🇭🇰', 'TW': '🇹🇼', 'AU': '🇦🇺', 'NZ': '🇳🇿', 'AR': '🇦🇷',
        'CL': '🇨🇱', 'MX': '🇲🇽', 'CO': '🇨🇴', 'PE': '🇵🇪', 'ZA': '🇿🇦',
        'EG': '🇪🇬', 'NG': '🇳🇬', 'KE': '🇰🇪', 'MA': '🇲🇦', 'TH': '🇹🇭',
        'VN': '🇻🇳', 'MY': '🇲🇾', 'ID': '🇮🇩', 'PH': '🇵🇭', 'IL': '🇮🇱',
        'SA': '🇸🇦', 'QA': '🇶🇦', 'KW': '🇰🇼', 'OM': '🇴🇲', 'IQ': '🇮🇶',
        'IR': '🇮🇷', 'PK': '🇵🇰', 'BD': '🇧🇩', 'LK': '🇱🇰', 'NP': '🇳🇵',
        'MM': '🇲🇲', 'KH': '🇰🇭', 'LA': '🇱🇦', 'MN': '🇲🇳', 'GE': '🇬🇪',
        'AM': '🇦🇲', 'AZ': '🇦🇿', 'AL': '🇦🇱', 'BA': '🇧🇦', 'HR': '🇭🇷',
        'RS': '🇷🇸', 'BG': '🇧🇬', 'RO': '🇷🇴', 'HU': '🇭🇺', 'SK': '🇸🇰',
        'CZ': '🇨🇿', 'AT': '🇦🇹', 'CH': '🇨🇭', 'BE': '🇧🇪', 'PT': '🇵🇹',
        'GR': '🇬🇷', 'DK': '🇩🇰', 'NO': '🇳🇴', 'SE': '🇸🇪', 'FI': '🇫🇮',
        'IE': '🇮🇪', 'LT': '🇱🇹', 'LV': '🇱🇻', 'EE': '🇪🇪', 'BY': '🇧🇾',
        'MD': '🇲🇩', 'KG': '🇰🇬', 'UZ': '🇺🇿', 'TJ': '🇹🇯', 'TM': '🇹🇲',
        'MN': '🇲🇳', 'KP': '🇰🇵', 'CU': '🇨🇺', 'VE': '🇻🇪', 'UY': '🇺🇾',
        'PY': '🇵🇾', 'BO': '🇧🇴', 'EC': '🇪🇨', 'CR': '🇨🇷', 'PA': '🇵🇦',
        'DO': '🇩🇴', 'HT': '🇭🇹', 'JM': '🇯🇲', 'BS': '🇧🇸', 'BB': '🇧🇧',
        'TT': '🇹🇹', 'BN': '🇧🇳', 'MV': '🇲🇻', 'SC': '🇸🇨', 'MU': '🇲🇺',
        'MT': '🇲🇹', 'CY': '🇨🇾', 'IS': '🇮🇸', 'LU': '🇱🇺', 'MC': '🇲🇨',
        'LI': '🇱🇮', 'AD': '🇦🇩', 'SM': '🇸🇲', 'VA': '🇻🇦', 'AG': '🇦🇬',
        'GD': '🇬🇩', 'LC': '🇱🇨', 'VC': '🇻🇨', 'DM': '🇩🇲', 'KN': '🇰🇳',
        'FJ': '🇫🇯', 'SB': '🇸🇧', 'VU': '🇻🇺', 'WS': '🇼🇸', 'TO': '🇹🇴',
        'KI': '🇰🇮', 'MH': '🇲🇭', 'FM': '🇫🇲', 'PW': '🇵🇼', 'TV': '🇹🇻',
        'NR': '🇳🇷'
    }
    return flags.get(code.upper(), '🌍')
