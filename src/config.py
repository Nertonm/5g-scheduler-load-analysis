"""Configuração do projeto 5G scheduler load analysis.

Este módulo é a fonte única dos parâmetros do experimento.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Config:
    """Parâmetros do experimento.

    Cada campo corresponde a uma decisão de desenho do experimento.
    (não há fonte externa que os sobrescreva).
    """

    # Topologia: 1 célula, SISO
    # num_cells=1 elimina interferência intercelular, isolando o efeito do
    # scheduler. is_siso=True remove MIMO como fator de confusão. Isso
    # permite atribuir mudanças nas métricas apenas à política de scheduling.
    num_cells: int = 1
    is_siso: bool = True

    # cell_radius_m: raio geométrico usado para posicionar os UEs (metros).
    #
    # Delimitação do cenário: o canal base usa RayleighBlockFading sem
    # path loss, shadowing ou dependência da distância gNB-UE. Portanto,
    # todos os UEs possuem a mesma distribuição de SNR média por construção:
    # cell_radius_m e a posição do UE não são fontes de heterogeneidade de
    # canal neste experimento.
    #
    # O cenário isola a diversidade multiusuário temporal: Max C/I explora
    # realizações instantâneas favoráveis do fading; RR ignora o canal; PF
    # combina taxa instantânea e histórico. Assim, os resultados não devem
    # ser interpretados como avaliação de justiça entre UEs near/far ou de
    # cobertura espacial. Modelos com path loss/3GPP são extensões possíveis,
    # mas não parte deste desenho causal controlado.
    cell_radius_m: float = 500.0

    # Carga de usuários: as cargas testadas, em número de UEs simultâneos.
    # A varredura 2 a 32 é o eixo de estresse: a pergunta central é em qual
    # carga o Max C/I cruza o limiar de justiça (JFI < 0,5).
    #
    # default_factory (e nao default direto): listas sao mutaveis; em dataclass
    # um default mutavel seria compartilhado entre todas as instancias de Config.
    # field(default_factory=lambda: [...]) cria uma lista nova por instancia.
    #
    # Progressao geometrica (dobra a cada passo) e deliberada: a diversidade
    # multiusuario do Max C/I cresce como log(N) (Tse & Viswanath), entao os
    # pontos ficam igualmente espacados na escala log, onde a metrica e
    # aproximadamente linear. Espacamento aritmetico espremeria a alta carga.
    #
    # Conflito de desenho: 5 niveis geometricos sao
    # otimos para estimar o LD50 (pergunta central) mas insuficientes para
    # modelagem formal da forma da curva (AIC/BIC arriscado com 5 pontos)
    # Extensao possivel: adicionar 6, 12, 24, 48 se a modelagem de forma for priorizada.
    user_counts: list[int] = field(default_factory=lambda: [2, 4, 8, 16, 32])

    # Canal: Rayleigh (RayleighBlockFading no Sionna).
    # Modela urbano sem linha de visada. O fading gera a heterogeneidade de
    # canal que os schedulers disputam; sem ela as políticas dariam o mesmo
    # resultado. Modelos TR 38.901/TDL foram descartados porque adicionam path
    # loss e Doppler que diluiriam a atribuição causal scheduler-métrica.
    channel_model: str = "rayleigh"

    # enable_pathloss: aplica path loss log-distance por posicao de UE
    # (cena heterogenea near/far). Quando False (default, decisao do Card 1),
    # a SNR media e identica entre UEs por construcao. Quando True, usa a
    # funcao apply_pathloss de src/channel.py.
    enable_pathloss: bool = False

    # pathloss_alpha: expoente de perda do modelo log-distance
    #   P(d) = P0 * (d0/d)^alpha   (redes sem fio: alpha 2 a 4).
    # 2=espaco livre, 3-4 urbano denso. So tem efeito se enable_pathloss=True.
    pathloss_alpha: float = 3.0

    # pathloss_d0_m / pathloss_radius_m: distancia de referencia (m) do modelo
    # log-distance e raio da celula usado para posicionar os UEs.
    pathloss_d0_m: float = 10.0
    pathloss_radius_m: float = 500.0

    # bandwidth_hz: largura de banda total (Hz). 20 MHz = configuração típica
    # 5G NR band n78.
    bandwidth_hz: float = 20e6

    # num_prbs: Physical Resource Blocks. 52 PRBs em 20 MHz com 30 kHz de
    # subcarrier. É a unidade de alocação que os schedulers disputam a cada TTI.
    #
    # O valor de 52 PRBs é decisão de desenho alinhada ao TAREFAS e ao checkpoint
    # do projeto (o tutorial Scheduling do Sionna usa a mesma ordem de grandeza).
    # A TS 38.101-1, Tabela 5.3.2-1, lista 51 PRBs para 20 MHz @ 30 kHz SCS
    # (52 PRBs é a configuração de 10 MHz @ 15 kHz); a diferença de 1 PRB não
    # altera a comparação relativa entre schedulers (objetivo do projeto).
    # Banda ocupada: 52 x 12 x 30 kHz = 18,72 MHz; o restante até 20 MHz é guard band.
    num_prbs: int = 52

    # subcarrier_spacing_hz: espaçamento entre subportadoras (Hz). 30 kHz é a
    # numerologia 5G NR padrão para bandas médias (n78).
    subcarrier_spacing_hz: float = 30e3

    # carrier_freq_hz: frequência da portadora (Hz). 3.5 GHz = band n78.
    carrier_freq_hz: float = 3.5e9

    # num_ttis: Transmission Time Intervals simulados por seed. Cada TTI = 1 ms,
    # então 10.000 TTIs = 10 s de rádio simulado por seed. Precisa ser alto o
    # suficiente para convergência estatística (risco documentado no checkpoint:
    # 10^4 pode ser pouco para PF em alguns cenários).
    num_ttis: int = 10000

    # num_seeds: sementes aleatórias independentes. Cada seed gera um canal
    # Rayleigh diferente. As 50 seeds formam a amostra para IC de 95% e testes
    # de hipótese (unidade amostral = seed). Valor canônico do estudo
    # consolidado (scripts/estudo_consolidado.py e Makefile usam --seeds 50).
    num_seeds: int = 50

    # tti_duration: duração de cada TTI (segundos). 1 ms é o TTI nominal.
    tti_duration: float = 1e-3

    # link_direction: sentido do enlace simulado. Alinhado no checkpoint como
    # DOWNLINK: tráfego real é assimétrico (downlink domina o volume e é o KPI
    # primário), e a decisão de scheduling é centralizada no gNB, sem a
    # complexidade de grants do uplink. O full-buffer abaixo é escolha de
    # tráfego, independente do link.
    link_direction: str = "downlink"

    # traffic: "full_buffer" = sempre há dados para todos os UEs. É o pior caso
    # para justiça (disputa real por recursos em todo TTI) e o cenário padrão
    # para isolar o efeito do scheduler.
    traffic: str = "full_buffer"

    # snr_db: SNR média de referência por UE (dB), por construção do cenário.
    # Sem path loss, E[|h|^2]=1 para todos os UEs, logo E[SNR_u] = ref_linear
    # é idêntica para todo UE. A posição (cell_radius_m) não é fonte de
    # heterogeneidade. O valor define a escala absoluta de throughput
    # (Shannon com cap), não a ordenação relativa entre schedulers.
    snr_db: float = 10.0

    # max_spectral_efficiency: cap de eficiência espectral (bit/s/Hz) no
    # mapeamento Shannon. Modela MCS finito (sem tabela TS 38.214 no card 1,
    # decisão documentada) e evita caudas pesadas de log2(1+SNR) em SNR alta.
    # 6.0 bit/s/Hz é um teto típico de 64-QAM com code rate ~1 (5G NR).
    max_spectral_efficiency: float = 6.0

    # Schedulers: as três políticas comparadas.
    schedulers: list[str] = field(
        default_factory=lambda: ["round_robin", "max_c_i", "proportional_fair"]
    )

    # pf_beta: fator de desconto geométrico da média histórica de throughput.
    # PF escolhe u = argmax(taxa_instantanea / media_historica), e a média é
    # atualizada como T_t = beta*T_{t-1} + (1-beta)*R_t. beta próximo de 1 =
    # média de longo prazo (PF mais estável). Default Sionna: 0.98. Este valor
    # deve ser declarado no relatório, pois muda JFI e throughput (viés de
    # implementação).
    pf_beta: float = 0.98

    # metrics: o que a simulação exporta por (scheduler, carga, seed).
    # O insumo bruto é throughput_per_ue: o throughput de CADA UE por seed
    # (não só a média). Todas as métricas derivadas (JFI, delta JFI, CDF,
    # 5th percentile, e as do trabalho IAD: Gini, família de Chiang) são
    # calculadas a partir dessa série completa. Sem ela, o Eixo 1 do
    # trabalho IAD (robustez à métrica) não pode ser executado.
    # delta_jfi_relative_to_rr é a diferença de JFI de cada scheduler contra o
    # RR (piso de justiça), métrica central do trabalho IAD.
    export_per_ue: bool = True  # salvar throughput de cada UE por seed
    metrics: list[str] = field(
        default_factory=lambda: [
            "throughput_aggregate",
            "throughput_mean_per_ue",
            "jains_fairness_index",
            "throughput_5th_percentile",
            "delta_jfi_relative_to_rr",
            "cdf_throughput",
        ]
    )

    # Saída: onde gravar resultados e se gerar gráficos.
    save_results: bool = True
    results_dir: str = "results/"
    generate_plots: bool = True

    @classmethod
    def load(cls) -> "Config":
        """Retorna a configuração do experimento.

        Mantém a assinatura de carga por compatibilidade; como não há fonte
        externa, retorna a instância padrão com os valores reais.
        """
        return cls()

    @property
    def occupied_bandwidth_hz(self) -> float:
        """Banda efetivamente ocupada pelos PRBs (Hz).

        num_prbs * 12 subcarriers * subcarrier_spacing. Em 20 MHz nominal com
        52 PRBs dá ~18.72 MHz, o restante é guard band.
        """
        return self.num_prbs * 12 * self.subcarrier_spacing_hz

    @property
    def sim_duration_per_seed_s(self) -> float:
        """Tempo de rádio simulado por seed (segundos)."""
        return self.num_ttis * self.tti_duration

    @property
    def total_simulations(self) -> int:
        """Número total de simulações: cargas x schedulers x seeds."""
        return len(self.user_counts) * len(self.schedulers) * self.num_seeds


def load_config() -> Config:
    """Conveniência: carrega a configuração padrão do experimento."""
    return Config.load()
