import re


def validate_rut(rut: str) -> bool:
    """Validates a Chilean RUT (Rol Único Tributario)."""
    rut = rut.upper()
    rut = re.sub(r'[^0-9Kk]+', '', rut)

    if not rut or len(rut) < 2:
        return False

    body = rut[:-1]
    dv = rut[-1]

    if not body.isdigit():
        return False

    reversed_body = body[::-1]
    factor = 2
    sum_ = 0
    for digit in reversed_body:
        sum_ += int(digit) * factor
        factor += 1
        if factor == 8:
            factor = 2

    calculated_dv = 11 - (sum_ % 11)
    if calculated_dv == 11:
        calculated_dv_str = '0'
    elif calculated_dv == 10:
        calculated_dv_str = 'K'
    else:
        calculated_dv_str = str(calculated_dv)

    return calculated_dv_str == dv
