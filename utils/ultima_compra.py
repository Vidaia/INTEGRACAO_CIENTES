import pandas as pd

def ultimacompra(apply_value, ultimaCompra):
    ultcompra = ultimaCompra[ultimaCompra['codigoCliente'] == apply_value]
    ultima_data = pd.to_datetime(ultcompra['data'].max())
    return ultima_data if not pd.isnull(ultima_data) else pd.to_datetime('1900-01-01').date()