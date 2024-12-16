import phonenumbers

def ajustar_numero(numero):
    numero = ''.join(filter(str.isdigit, numero))
    if numero.startswith('55') and len(numero) == 12:
        return numero
    if len(numero) == 8:
        numero = '51' + '9' + numero
    elif len(numero) == 9:
        numero = '51' + numero
    elif len(numero) == 10:
        numero = numero[:2] + '9' + numero[2:]
    elif len(numero) == 11:
        numero = '55' + numero
    return numero

def padronizar_telefone_brasileiro(numero):
    try:
        numero_ajustado = ajustar_numero(numero)
        telefone_obj = phonenumbers.parse(numero_ajustado, "BR")
        if phonenumbers.is_valid_number(telefone_obj):
            telefone_formatado = phonenumbers.format_number(telefone_obj, phonenumbers.PhoneNumberFormat.E164)
            return telefone_formatado
        else:
            return numero
    except phonenumbers.NumberParseException:
        return numero