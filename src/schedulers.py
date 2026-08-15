"""Implementação dos schedulers (Card 3: Max C/I)"""


from __future__ import annotations
import numpy as np

class MaxCIScheduler:
    """Scheduler Max C/I (Maximum Carrier-to-Interference / Best Channel).

    A cada TTI t, seleciona o UE com a maior taxa instantânea r_i(t):
        u(t) = argmax_i r_i(t)

    Totalmente focado na eficiência espectral da célula, ignorando a equidade (JFI).
    """

    def __init__(self, num_ues: int) -> None:
       self.num_ues = num_ues
    
    def select(self, tti: int, rates: np.ndarray) -> int:
        """Seleciona o UE com a maior taxa instantânea no TTI t.

        rates: [num_ues] float, taxa instantânea realizável de cada UE no TTI.
        Retorna o índice (0 .. num_ues - 1) do UE com maior taxa.
        """
        if len(rates) == 0:
            return -1
        #u(t) = argmax_i r_i(t)
        return int(np.argmax(rates))    
    
    def update(self, tti: int, ue: int, rate: float) -> None:
        """Hook pós-alocação.
        
        O Max C/I é sem memória (não guarda histórico de throughput).
        Portanto, esta função é um no-op.
        """
        pass
    
def create_scheduler(name: str, num_ues: int):
    if name == "empty":
        # Import local ou definição da EmptyScheduler
        from src.simulation import EmptyScheduler
        return EmptyScheduler(num_ues)
    elif name == "max_c_i":
        return MaxCIScheduler(num_ues)
    else:
        raise NotImplementedError(f"Scheduler '{name}' não implementado.")