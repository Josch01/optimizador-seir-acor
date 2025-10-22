# -*- coding: utf-8 -*-
import math
from dataclasses import dataclass

def parse_numeric(expr: str) -> float:
    """Eval\u00faa de forma segura una expresi\u00f3n matem\u00e1tica simple."""
    if not isinstance(expr, str) or not expr.strip():
        raise ValueError("La expresi\u00f3n no puede estar vac\u00eda.")
    
    s = expr.strip().replace('^', '**').replace('math.pi', 'pi').replace('np.pi', 'pi').replace('PI', 'pi').replace('Pi', 'pi')
    
    safe_globals = {"__builtins__": {}}
    safe_locals = {"pi": math.pi}
    
    try:
        return float(eval(s, safe_globals, safe_locals))
    except Exception as e:
        raise ValueError(f"Expresi\u00f3n inv\u00e1lida: '{expr}'") from e

@dataclass
class ACORConfig:
    """Configuraci\u00f3n para el optimizador ACOR."""
    n_ants: int = 90
    archive_size: int = 40
    max_iter: int = 1500
    q: float = 0.7

    # Modelo Multi-Colonia
    colonies_count: int = 4
    migration_interval: int = 25
    migration_size: int = 2

    # B\u00fasqueda local
    local_search_enabled: bool = True
    local_search_radius: float = 0.1
    local_search_points: int = 10
    local_search_frequency: int = 5

    # Aprendizaje Basado en Oposici\u00f3n (OBL)
    obl_enabled: bool = True

    # Pulido Codicioso (Greedy Refinement)
    refinement_enabled: bool = True
    refinement_frequency: int = 50
    refinement_step: float = 0.05
