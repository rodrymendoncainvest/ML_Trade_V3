# labels.py

def generate_labels_multiclass(df, future_column="future_return_pct"):
    """
    Retorna labels de 0 a 4 para 5 quantis.
    """
    return pd.qcut(df[future_column], 5, labels=[0,1,2,3,4])
