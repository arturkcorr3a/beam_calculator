# type: ignore

# cSpell:disable

from src.analysis.model import BeamSupport, DistributedLoad
from src.analysis.solver import analyse_beam
from src.calculators.rebar_calculator import RebarCalculator
from src.calculators.stirrup_calculator import StirrupCalculator
from src.calculators.stirrup_rebar_coordinator import coordinate_span
from src.config import APP_CONFIG
from src.loading.forces import design_effort_elu
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.stirrups import Stirrups
from src.structural_elements.rectangular_beam import RectangularBeam

# ==============================================================================
# 1. INPUT DATA / DADOS DE ENTRADA
# ==============================================================================
span1 = 621.5  # cm
span2 = 620  # cm
span3 = 781.5  # cm
length = span1 + span2 + span3  # cm

width = 19  # cm
height = 65  # cm

APP_CONFIG.pavement_concrete = Concrete.C40
steel = Steel.CA50

# Contínua (sem considerações de rigidez)
p1 = BeamSupport(0)
p2 = BeamSupport(span1)
p3 = BeamSupport(span1 + span2)
p4 = BeamSupport(length)

# Carregamento (sinal positivo pq é para baixo)
load1 = 15.710  # kN/m 20.3 #
load2 = 14.479  # kN/m 20.3 #
load3 = 31.672  # kN/m 20.3 #

load_span1 = DistributedLoad(0, span1, load1)
load_span2 = DistributedLoad(span1, span1 + span2, load2)
load_span3 = DistributedLoad(span1 + span2, length, load3)

supports = [p1, p2, p3, p4]
loads = [load_span1, load_span2, load_span3]

beam = RectangularBeam(length, width, height, steel)
analysis = analyse_beam(beam, supports, loads)

# ==============================================================================
# 2. STRUCTURAL ANALYSIS / ESFORÇOS SOLICITANTES
# ==============================================================================
interest_points = analysis.moment_extremes_per_segment()
position, max_bending_moment = max(
    interest_points, key=lambda point: abs(point[1])
)  # kN.m
max_shear_force = analysis.max_abs_shear()  # kN

design_bending_moment = design_effort_elu(max_bending_moment)  # kN.m
design_shear_force = design_effort_elu(max_shear_force)  # kN

# ==============================================================================
# 3. CALCULATIONS / PROCESSAMENTO DO DIMENSIONAMENTO
# ==============================================================================
stirrup_calculator = StirrupCalculator(beam, design_shear_force)
stirrups = Stirrups(beam, stirrup_calculator)

calculator = RebarCalculator(
    beam=beam,
    bending_moment=design_bending_moment,
    bending_moment_position=position,
)
coordinate_span([calculator], stirrups)

compressed = calculator.compressed_reinforcement
tensioned = calculator.tensioned_reinforcement
