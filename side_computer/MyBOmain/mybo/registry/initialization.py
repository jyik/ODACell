from sympy import sympify


def compute_doe(doe_expr: str, dimension: int) -> int:
    doe_sym = sympify(doe_expr)
    num_doe = doe_sym.subs('D', dimension)
    return int(num_doe)