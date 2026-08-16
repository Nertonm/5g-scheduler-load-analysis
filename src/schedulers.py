from __future__ import annotations

import numpy as np


class ProportionalFair:
    """
    Scheduler Proportional Fair (PF).

    A cada TTI, escolhe o UE que maximiza:

        R_u(t) / T_u(t)

    onde:
        R_u(t) = taxa instantânea alcançável pelo UE;
        T_u(t) = média histórica de throughput do UE.

    Após a alocação, o histórico é atualizado por:

        T_u(t) = beta * T_u(t-1) + (1 - beta) * R_u(t)

    Para UEs não escalonados naquele TTI, R_u(t) = 0.

    Essa implementação segue o contrato definido em src/simulation.py:
        select(tti, rates) -> int
        update(tti, ue, rate) -> None
    """

    def __init__(self, num_ues: int, beta: float = 0.98):
        """
        Inicializa o estado do scheduler.

        Parameters
        ----------
        num_ues : int
            Número de User Equipments disputando o recurso.

        beta : float
            Fator de esquecimento da média histórica.
            No cenário do projeto, beta = 0.98.
            Quanto mais próximo de 1, maior o peso do histórico.
        """

        if num_ues <= 0:
            raise ValueError("num_ues deve ser maior que zero.")

        if not 0.0 <= beta < 1.0:
            raise ValueError("beta deve estar no intervalo [0, 1).")

        self.num_ues = num_ues
        self.beta = beta

        # Histórico T_u de cada UE.
        #
        # O valor inicial 1.0 evita divisão por zero no primeiro TTI
        # e mantém todos os UEs inicialmente em condições iguais.
        self.t_hist = np.ones(num_ues, dtype=np.float64)

    def select(self, tti: int, rates: np.ndarray) -> int:
        """
        Escolhe o UE que receberá o recurso no TTI atual.

        Parameters
        ----------
        tti : int
            Índice do TTI atual.
            Não entra diretamente na fórmula do PF, mas faz parte
            da interface comum definida pelo simulation.py.

        rates : np.ndarray
            Vetor [num_ues] contendo a taxa instantânea realizável
            de cada UE em bit/s.

        Returns
        -------
        int
            Índice do UE que maximiza R_u(t) / T_u(t).
        """

        rates = np.asarray(rates, dtype=np.float64)

        if rates.shape != (self.num_ues,):
            raise ValueError(
                f"rates deve possuir shape ({self.num_ues},), "
                f"mas recebeu {rates.shape}."
            )

        if not np.all(np.isfinite(rates)):
            raise ValueError("rates contém NaN ou infinito.")

        if np.any(rates < 0):
            raise ValueError("rates não pode conter taxas negativas.")

        # Métrica Proportional Fair:
        #
        #        taxa instantânea R_u(t)
        # PF_u = -------------------------
        #        histórico de taxa T_u(t)
        metric = rates / self.t_hist

        return int(np.argmax(metric))

    def update(self, tti: int, ue: int, rate: float) -> None:
        """
        Atualiza o histórico de throughput após a alocação.

        Parameters
        ----------
        tti : int
            Índice do TTI atual.

        ue : int
            UE escolhido pelo método select().

        rate : float
            Taxa efetivamente alcançada pelo UE selecionado.
        """

        if not 0 <= ue < self.num_ues:
            raise ValueError(
                f"ue deve estar entre 0 e {self.num_ues - 1}."
            )

        if not np.isfinite(rate) or rate < 0:
            raise ValueError("rate deve ser um número finito e não-negativo.")

        # R_t contém a taxa efetivamente recebida no TTI.
        #
        # Somente o UE escalonado recebe throughput.
        # Para os demais UEs, R_t = 0.
        r_t = np.zeros(self.num_ues, dtype=np.float64)
        r_t[ue] = rate

        # Média móvel exponencial:
        #
        # T_t = beta * T_(t-1) + (1-beta) * R_t
        self.t_hist = (
            self.beta * self.t_hist
            + (1.0 - self.beta) * r_t
        )


class RoundRobin:
    """
    Scheduler Round Robin (RR).

    A cada TTI, o recurso é atribuído ao próximo UE em ordem cíclica:

        UE0 → UE1 → UE2 → ... → UEn → UE0

    Essa implementação segue o contrato definido em src/simulation.py:
        select(tti, rates) -> int
        update(tti, ue, rate) -> None
    """

    def __init__(self, num_ues: int):
        """
        Inicializa o scheduler Round Robin.

        Parameters
        ----------
        num_ues : int
            Número de User Equipments.
        """

        if num_ues <= 0:
            raise ValueError("num_ues deve ser maior que zero.")

        self.num_ues = num_ues

        # Índice do próximo UE a ser escalonado
        self.current = 0

    def select(self, tti: int, rates: np.ndarray) -> int:
        """
        Seleciona o próximo UE em ordem circular.

        Parameters
        ----------
        tti : int
            Índice do TTI atual (não utilizado).

        rates : np.ndarray
            Vetor de taxas instantâneas.
            É validado apenas para manter compatibilidade com a interface.

        Returns
        -------
        int
            Índice do UE selecionado.
        """

        rates = np.asarray(rates)

        if rates.shape != (self.num_ues,):
            raise ValueError(
                f"rates deve possuir shape ({self.num_ues},), "
                f"mas recebeu {rates.shape}."
            )

        ue = self.current
        self.current = (self.current + 1) % self.num_ues

        return ue

    def update(self, tti: int, ue: int, rate: float) -> None:
        """
        Atualização do estado.

        No Round Robin não há histórico nem métricas a atualizar.
        O método existe apenas para manter a mesma interface dos
        demais schedulers.
        """

        if not 0 <= ue < self.num_ues:
            raise ValueError(
                f"ue deve estar entre 0 e {self.num_ues - 1}."
            )

        if not np.isfinite(rate) or rate < 0:
            raise ValueError(
                "rate deve ser um número finito e não-negativo."
            )

        # Round Robin não atualiza nenhum estado baseado na taxa.
        pass


class MaxCIScheduler:
    """Scheduler Max C/I (Maximum Carrier-to-Interference / Best Channel).

    A cada TTI t, seleciona o UE com a maior taxa instantânea r_i(t):
        u(t) = argmax_i r_i(t)

    Totalmente focado na eficiência espectral da célula, ignorando a equidade (JFI).
    """

    def __init__(self, num_ues: int) -> None:
        if num_ues <= 0:
            raise ValueError("num_ues deve ser maior que zero.")
        self.num_ues = num_ues
    
    def select(self, tti: int, rates: np.ndarray) -> int:
        """Seleciona o UE com a maior taxa instantânea no TTI t.

        rates: [num_ues] float, taxa instantânea realizável de cada UE no TTI.
        Retorna o índice (0 .. num_ues - 1) do UE com maior taxa.
        """
        rates = np.asarray(rates)

        if rates.shape != (self.num_ues,):
            raise ValueError(
                f"rates deve possuir shape ({self.num_ues},), "
                f"mas recebeu {rates.shape}."
            )

        # u(t) = argmax_i r_i(t)
        return int(np.argmax(rates))    
    
    def update(self, tti: int, ue: int, rate: float) -> None:
        """Hook pós-alocação.
        
        O Max C/I é sem memória (não guarda histórico de throughput).
        Portanto, esta função é um no-op.
        """
        pass
    
def create_scheduler(name: str, num_ues: int, **kwargs):
    """Factory dos schedulers.

    Mapeia o nome do scheduler (mesmo formato do config) para a classe
    correspondente. Contrato comum:
        select(tti, rates) -> int
        update(tti, ue, rate) -> None

    Parameters
    ----------
    name : str
        Nome do scheduler: "empty", "round_robin", "max_c_i" ou
        "proportional_fair".
    num_ues : int
        Numero de UEs do cenario.
    **kwargs
        Parametros extras, ex.: beta para o ProportionalFair.
    """
    if name == "empty":
        # Import local para evitar ciclo (EmptyScheduler vive em simulation).
        from src.simulation import EmptyScheduler
        return EmptyScheduler(num_ues)
    elif name == "round_robin":
        return RoundRobin(num_ues)
    elif name == "max_c_i":
        return MaxCIScheduler(num_ues)
    elif name == "proportional_fair":
        return ProportionalFair(num_ues, beta=kwargs.get("beta", 0.98))
    else:
        raise NotImplementedError(f"Scheduler '{name}' não implementado.")
